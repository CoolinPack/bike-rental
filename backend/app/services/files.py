import asyncio
import logging
import os
import re
import uuid
from pathlib import Path
from urllib.parse import urlparse

import aiofiles
from fastapi import UploadFile

from app.config import settings

logger = logging.getLogger(__name__)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/webm"}

MAX_IMAGE_SIZE = 10 * 1024 * 1024
MAX_VIDEO_SIZE = 50 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024


def _ext_for_type(content_type: str) -> str:
    return {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "video/mp4": ".mp4",
        "video/quicktime": ".mov",
        "video/webm": ".webm",
    }.get(content_type, "")


def _cloudinary_client():
    if settings.cloudinary_partially_configured:
        raise RuntimeError(
            "Cloudinary is only partially configured. Set CLOUDINARY_CLOUD_NAME, "
            "CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET in Render."
        )
    if not settings.cloudinary_enabled:
        return None

    try:
        import cloudinary
    except ImportError as exc:
        raise RuntimeError(
            "Cloudinary credentials are configured but the cloudinary package is missing."
        ) from exc

    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True,
    )
    return cloudinary


def _upload_to_cloudinary(content: bytes, kind: str, extension: str) -> str:
    cloudinary = _cloudinary_client()
    if cloudinary is None:
        raise RuntimeError("Cloudinary is not configured")

    result = cloudinary.uploader.upload(
        content,
        resource_type="image" if kind == "image" else "video",
        folder=f"bike-rental/{kind}s",
        public_id=uuid.uuid4().hex,
        use_filename=False,
        unique_filename=False,
        overwrite=False,
    )
    secure_url = result.get("secure_url")
    if not secure_url:
        raise RuntimeError("Cloudinary did not return a secure URL")
    return secure_url


async def save_upload(file: UploadFile, kind: str) -> str:
    if kind == "image":
        if file.content_type not in ALLOWED_IMAGE_TYPES:
            raise ValueError(f"Unsupported image type: {file.content_type}")
        max_size = MAX_IMAGE_SIZE
    elif kind == "video":
        if file.content_type not in ALLOWED_VIDEO_TYPES:
            raise ValueError(f"Unsupported video type: {file.content_type}")
        max_size = MAX_VIDEO_SIZE
    else:
        raise ValueError("kind must be 'image' or 'video'")

    ext = _ext_for_type(file.content_type) or Path(file.filename or "").suffix.lower()
    if not ext:
        raise ValueError("Cannot determine file extension")

    # Read and validate fully before publishing a URL. This prevents partial uploads
    # from being added to a bike record.
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_size:
            raise ValueError(f"File too large (max {max_size} bytes)")
        chunks.append(chunk)
    if total == 0:
        raise ValueError("Uploaded file is empty")
    content = b"".join(chunks)

    if settings.cloudinary_enabled or settings.cloudinary_partially_configured:
        return await asyncio.to_thread(_upload_to_cloudinary, content, kind, ext)

    # Local fallback is retained for local development. On Render, configure
    # Cloudinary; the ephemeral local filesystem is not durable across deploys.
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}{ext}"
    final_path = upload_dir / name
    temp_path = upload_dir / f".{name}.uploading"
    try:
        async with aiofiles.open(temp_path, "wb") as f:
            await f.write(content)
        os.replace(temp_path, final_path)
    except Exception:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return f"/uploads/{name}"


def _cloudinary_public_id(url: str) -> tuple[str, str] | None:
    parsed = urlparse(url)
    if parsed.netloc.lower() not in {"res.cloudinary.com", "www.res.cloudinary.com"}:
        return None
    parts = [part for part in parsed.path.split("/") if part]
    # Expected path: /<cloud_name>/<resource_type>/upload/[v123]/<public_id>.<ext>
    try:
        upload_index = parts.index("upload")
    except ValueError:
        return None
    if upload_index < 1 or upload_index + 1 >= len(parts):
        return None
    resource_type = parts[upload_index - 1]
    if resource_type not in {"image", "video"}:
        return None
    public_parts = parts[upload_index + 1:]
    if public_parts and re.fullmatch(r"v\d+", public_parts[0]):
        public_parts = public_parts[1:]
    if not public_parts:
        return None
    public_parts[-1] = public_parts[-1].rsplit(".", 1)[0]
    public_id = "/".join(public_parts)
    return resource_type, public_id


def delete_upload(url: str) -> None:
    if url.startswith("/uploads/"):
        name = url.removeprefix("/uploads/")
        # Prevent path traversal from malformed database values.
        if Path(name).name != name:
            return
        path = Path(settings.upload_dir) / name
        try:
            if path.is_file():
                path.unlink()
        except OSError:
            logger.exception("Failed to delete local upload %s", name)
        return

    cloudinary_info = _cloudinary_public_id(url)
    if not cloudinary_info:
        return
    resource_type, public_id = cloudinary_info
    try:
        cloudinary = _cloudinary_client()
        if cloudinary is not None:
            cloudinary.uploader.destroy(
                public_id,
                resource_type=resource_type,
                invalidate=True,
            )
    except Exception:
        # Keep the database operation from failing because a remote cleanup failed.
        logger.exception("Failed to delete Cloudinary asset %s", public_id)
