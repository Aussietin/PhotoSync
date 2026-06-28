import uuid
from pathlib import Path

from fastapi import UploadFile

from config import settings
from services import heif_support  # noqa: F401 — registers HEIC opener with Pillow


async def save_upload(file: UploadFile) -> tuple[Path, Path | None, Path | None, int]:
    """Persist uploaded file. Returns (file_path, thumb_path, preview_path, size)."""
    suffix = Path(file.filename or "photo.jpg").suffix.lower()
    stem = uuid.uuid4().hex
    dest = Path(settings.UPLOAD_DIR) / f"{stem}{suffix}"

    data = await file.read()
    dest.write_bytes(data)

    thumb_path = await _make_thumbnail(dest, stem)
    preview_path = await _make_preview(dest, stem)
    return dest, thumb_path, preview_path, len(data)


def _downscale_jpeg(source: Path, out: Path, size) -> Path | None:
    """Open any supported image (incl. HEIC) and write a downscaled JPEG."""
    try:
        from PIL import Image, ImageOps

        with Image.open(source) as img:
            img = ImageOps.exif_transpose(img)  # honor orientation
            img.thumbnail(size, Image.LANCZOS)
            img = img.convert("RGB")
            out.parent.mkdir(parents=True, exist_ok=True)
            img.save(out, "JPEG", quality=85, optimize=True)
        return out
    except Exception:
        return None


async def _make_thumbnail(source: Path, stem: str) -> Path | None:
    out = Path(settings.THUMBNAIL_DIR) / f"{stem}_thumb.jpg"
    return _downscale_jpeg(source, out, settings.THUMBNAIL_SIZE)


async def _make_preview(source: Path, stem: str) -> Path | None:
    """Web-friendly JPEG so HEIC/large originals display in any browser."""
    out = Path(settings.PREVIEW_DIR) / f"{stem}_preview.jpg"
    return _downscale_jpeg(source, out, settings.PREVIEW_SIZE)
