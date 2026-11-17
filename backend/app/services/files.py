import os
import uuid
from pathlib import Path

import aiofiles
from fastapi import UploadFile

from app.config import settings


ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/webm"}

MAX_IMAGE_SIZE = 10 * 1024 * 1024
MAX_VIDEO_SIZE = 50 * 1024 * 1024


def _ext_for_type(content_type: str) -> str:
    return {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "video/mp4": ".mp4",
        "video/quicktime": ".mov",
        "video/webm": ".webm",
    }.get(content_type, "")


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

    ext = _ext_for_type(file.content_type) or Path(file.filename or "").suffix
    if not ext:
        raise ValueError("Cannot determine file extension")

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    name = f"{uuid.uuid4().hex}{ext}"
    path = upload_dir / name

    total = 0
    async with aiofiles.open(path, "wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_size:
                await f.close()
                try:
                    os.remove(path)
                except OSError:
                    pass
                raise ValueError(f"File too large (max {max_size} bytes)")
            await f.write(chunk)

    return f"/uploads/{name}"


def delete_upload(url: str) -> None:
    if not url.startswith("/uploads/"):
        return
    name = url.removeprefix("/uploads/")
    path = Path(settings.upload_dir) / name
    try:
        if path.is_file():
            path.unlink()
    except OSError:
        pass