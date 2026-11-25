
from __future__ import annotations

import asyncio
import logging
import os
import re
import uuid
from io import BytesIO
from pathlib import Path
from urllib.parse import unquote, urlparse

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


def _selected_backend() -> str:
    requested = (settings.storage_backend or "auto").strip().lower()

    if requested not in {"auto", "cloudinary", "s3", "local"}:
        raise RuntimeError(
            "STORAGE_BACKEND must be auto, cloudinary, s3, or local"
        )

    if requested == "auto":
        if settings.cloudinary_partially_configured:
            raise RuntimeError(
                "Cloudinary is partially configured. "
                "Set all Cloudinary credentials or clear them."
            )

        if settings.cloudinary_enabled:
            return "cloudinary"

        if settings.s3_enabled:
            return "s3"

        return "local"

    if requested == "cloudinary":
        if (
            settings.cloudinary_partially_configured
            or not settings.cloudinary_enabled
        ):
            raise RuntimeError(
                "STORAGE_BACKEND=cloudinary requires "
                "CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY "
                "and CLOUDINARY_API_SECRET"
            )

    if requested == "s3" and not settings.s3_enabled:
        raise RuntimeError(
            "STORAGE_BACKEND=s3 requires S3_BUCKET, "
            "S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY"
        )

    return requested


def _cloudinary_client():
    try:
        import cloudinary
        import cloudinary.uploader
    except ImportError as exc:
        raise RuntimeError(
            "Cloudinary is selected but the cloudinary package is missing"
        ) from exc

    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True,
    )

    return cloudinary


def _s3_client():
    try:
        import boto3
        from botocore.config import Config
    except ImportError as exc:
        raise RuntimeError(
            "S3 storage is selected but boto3 is not installed"
        ) from exc

    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url or None,
        region_name=settings.s3_region or None,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
        config=Config(s3={"addressing_style": "path"}),
    )


def _s3_public_url(key: str) -> str:
    if settings.s3_public_base_url:
        return f"{settings.s3_public_base_url.rstrip('/')}/{key}"

    if settings.s3_endpoint_url:
        return (
            f"{settings.s3_endpoint_url.rstrip('/')}/"
            f"{settings.s3_bucket}/{key}"
        )

    region = settings.s3_region or "us-east-1"

    return (
        f"https://{settings.s3_bucket}.s3."
        f"{region}.amazonaws.com/{key}"
    )


def _upload_to_cloudinary(
    content: bytes,
    kind: str,
    extension: str,
    park_id: int,
) -> str:
    cloudinary = _cloudinary_client()

    resource_type = "image" if kind == "image" else "video"
    object_name = uuid.uuid4().hex

    file_object = BytesIO(content)
    file_object.name = f"{object_name}{extension}"

    folder = f"bike-rental/parks/{park_id}/{kind}s"

    result = cloudinary.uploader.upload(
        file_object,
        resource_type=resource_type,
        folder=folder,
        public_id=object_name,
        use_filename=False,
        unique_filename=False,
        overwrite=False,
    )

    secure_url = result.get("secure_url")

    if not secure_url:
        raise RuntimeError("Cloudinary did not return a secure URL")

    return secure_url


def _upload_to_s3(
    content: bytes,
    kind: str,
    extension: str,
    park_id: int,
    content_type: str,
) -> str:
    key = f"parks/{park_id}/{kind}s/{uuid.uuid4().hex}{extension}"

    client = _s3_client()

    client.put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=content,
        ContentType=content_type,
        CacheControl="public, max-age=31536000, immutable",
    )

    return _s3_public_url(key)


async def save_upload(
    file: UploadFile,
    kind: str,
    park_id: int,
) -> str:
    if not isinstance(park_id, int) or park_id <= 0:
        raise ValueError("A valid park_id is required for file uploads")

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

    extension = (
        _ext_for_type(file.content_type)
        or Path(file.filename or "").suffix.lower()
    )

    if not extension:
        raise ValueError("Cannot determine file extension")

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

    backend = _selected_backend()

    if backend == "cloudinary":
        return await asyncio.to_thread(
            _upload_to_cloudinary,
            content,
            kind,
            extension,
            park_id,
        )

    if backend == "s3":
        return await asyncio.to_thread(
            _upload_to_s3,
            content,
            kind,
            extension,
            park_id,
            file.content_type,
        )

    # Local storage is for development or a persistent mounted volume only.
    relative_dir = Path("parks") / str(park_id) / f"{kind}s"
    upload_dir = Path(settings.upload_dir) / relative_dir

    upload_dir.mkdir(parents=True, exist_ok=True)

    name = f"{uuid.uuid4().hex}{extension}"
    final_path = upload_dir / name
    temp_path = upload_dir / f".{name}.uploading"

    try:
        async with aiofiles.open(temp_path, "wb") as output:
            await output.write(content)

        os.replace(temp_path, final_path)

    except Exception:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass

        raise

    return f"/uploads/{(relative_dir / name).as_posix()}"


def _cloudinary_public_id(url: str) -> tuple[str, str] | None:
    parsed = urlparse(url)

    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() not in {
            "res.cloudinary.com",
            "www.res.cloudinary.com",
        }
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
    ):
        return None

    parts = [part for part in parsed.path.split("/") if part]

    if len(parts) < 4:
        return None

    cloud_name = (settings.cloudinary_cloud_name or "").strip()

    if not cloud_name or parts[0] != cloud_name:
        return None

    try:
        upload_index = parts.index("upload")
    except ValueError:
        return None

    if upload_index != 2:
        return None

    resource_type = parts[1]

    if resource_type not in {"image", "video"}:
        return None

    public_parts = parts[upload_index + 1:]

    if public_parts and re.fullmatch(r"v\d+", public_parts[0]):
        public_parts = public_parts[1:]

    if not public_parts:
        return None

    if public_parts[0] != "bike-rental":
        return None

    if len(public_parts) < 4 or public_parts[1] != "parks":
        return None

    public_parts[-1] = public_parts[-1].rsplit(".", 1)[0]

    if not public_parts[-1]:
        return None

    return resource_type, "/".join(public_parts)


def _s3_key_from_url(url: str) -> str | None:
    """
    Return an S3 object key only when the URL matches configured storage.
    Credentials are not required for URL recognition.
    """
    parsed = urlparse(url)

    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username
        or parsed.password
    ):
        return None

    try:
        port = parsed.port
    except ValueError:
        return None

    path = unquote(parsed.path.lstrip("/"))

    if (
        not path
        or "\x00" in path
        or "\\" in path
        or any(part in {".", ".."} for part in path.split("/"))
    ):
        return None

    # Custom CDN domain or public bucket URL.
    if settings.s3_public_base_url:
        base = urlparse(settings.s3_public_base_url)

        try:
            base_port = base.port
        except ValueError:
            return None

        if (
            base.scheme != parsed.scheme
            or not base.netloc
            or parsed.netloc.lower() != base.netloc.lower()
            or port != base_port
        ):
            return None

        base_path = unquote(base.path.strip("/"))

        if base_path:
            prefix = base_path + "/"

            if not path.startswith(prefix):
                return None

            key = path[len(prefix):]
        else:
            key = path

        return key or None

    # S3-compatible endpoint, such as MinIO or Cloudflare R2.
    if settings.s3_endpoint_url:
        endpoint = urlparse(settings.s3_endpoint_url)

        try:
            endpoint_port = endpoint.port
        except ValueError:
            return None

        if (
            endpoint.scheme != parsed.scheme
            or not endpoint.netloc
            or parsed.netloc.lower() != endpoint.netloc.lower()
            or port != endpoint_port
        ):
            return None

        bucket = settings.s3_bucket

        if not bucket:
            return None

        prefix = f"{bucket}/"

        if not path.startswith(prefix):
            return None

        key = path[len(prefix):]
        return key or None

    # Standard AWS S3 virtual-hosted URLs.
    bucket = settings.s3_bucket

    if not bucket or parsed.scheme != "https" or port is not None:
        return None

    region = settings.s3_region or "us-east-1"

    expected_host = (
        f"{bucket}.s3.{region}.amazonaws.com"
    ).lower()

    if parsed.netloc.lower() == expected_host:
        return path

    legacy_host = f"{bucket}.s3.amazonaws.com".lower()

    if parsed.netloc.lower() == legacy_host:
        return path

    return None


def delete_upload(url: str) -> bool:
    """Delete a managed media object. Return True when deletion is complete."""
    if not url:
        return True

    # Local storage.
    if url.startswith("/uploads/"):
        relative = url.removeprefix("/uploads/")

        candidate = (Path(settings.upload_dir) / relative).resolve()
        root = Path(settings.upload_dir).resolve()

        try:
            candidate.relative_to(root)
        except ValueError:
            logger.warning("Rejected unsafe local upload path")
            return False

        try:
            if candidate.is_file():
                candidate.unlink()

            return True

        except OSError:
            logger.exception("Failed to delete local upload")
            return False

    # Cloudinary.
    cloudinary_info = _cloudinary_public_id(url)

    if cloudinary_info:
        resource_type, public_id = cloudinary_info

        try:
            cloudinary = _cloudinary_client()

            result = cloudinary.uploader.destroy(
                public_id,
                resource_type=resource_type,
                invalidate=True,
            )

            deletion_status = (
                result.get("result")
                if isinstance(result, dict)
                else None
            )

            if deletion_status in ("ok", "not found"):
                return True

            logger.warning(
                "Cloudinary deletion was not confirmed for %s: %s",
                public_id,
                result,
            )

            return False

        except Exception:
            logger.exception(
                "Failed to delete Cloudinary asset %s",
                public_id,
            )

            return False

    # S3 and S3-compatible storage.
    s3_key = _s3_key_from_url(url)

    if s3_key is not None:
        if not settings.s3_enabled:
            logger.error(
                "S3 media URL recognized, but S3 credentials or bucket "
                "configuration are missing. Object was not deleted."
            )
            return False

        try:
            _s3_client().delete_object(
                Bucket=settings.s3_bucket,
                Key=s3_key,
            )

            return True

        except Exception:
            logger.exception(
                "Failed to delete S3 object %s",
                s3_key,
            )

            return False

    # URL does not belong to a storage provider managed by this application.
    logger.info("Skipping unmanaged media URL: %s", url)

    return True
