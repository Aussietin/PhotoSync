import uuid
from pathlib import Path

from fastapi import UploadFile

from config import settings
from services import heif_support  # noqa: F401 — registers HEIC opener with Pillow


async def save_upload(file: UploadFile) -> tuple[Path, Path | None, int]:
    """Persist uploaded file and return (file_path, thumb_path, file_size)."""
    suffix = Path(file.filename or "photo.jpg").suffix.lower()
    stem = uuid.uuid4().hex
    dest = Path(settings.UPLOAD_DIR) / f"{stem}{suffix}"

    data = await file.read()
    dest.write_bytes(data)

    thumb_path = await _make_thumbnail(dest, stem)
    return dest, thumb_path, len(data)


async def _make_thumbnail(source: Path, stem: str) -> Path | None:
    try:
        from PIL import Image

        img = Image.open(source)
        img.thumbnail(settings.THUMBNAIL_SIZE, Image.LANCZOS)
        thumb = Path(settings.THUMBNAIL_DIR) / f"{stem}_thumb.jpg"
        img = img.convert("RGB")
        img.save(thumb, "JPEG", quality=85, optimize=True)
        return thumb
    except Exception:
        return None
