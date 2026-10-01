"""Photo -> JSON, and processor metadata -> Photo columns. Shared by every
route that returns photos (photos, albums, people, search)."""
import json
from pathlib import Path

from config import settings
from models.photo import Photo


def _photo_fields(metadata: dict) -> dict:
    """Map processor metadata to Photo column kwargs shared by upload/import."""
    return dict(
        width=metadata.get("width"),
        height=metadata.get("height"),
        taken_at=metadata.get("taken_at"),
        camera_make=metadata.get("camera_make"),
        camera_model=metadata.get("camera_model"),
        gps_lat=metadata.get("gps_lat"),
        gps_lon=metadata.get("gps_lon"),
        perceptual_hash=metadata.get("perceptual_hash"),
        quality_score=metadata.get("quality_score"),
        is_screenshot=metadata.get("is_screenshot", False),
        is_dark=metadata.get("is_dark", False),
        is_overexposed=metadata.get("is_overexposed", False),
        is_low_res=metadata.get("is_low_res", False),
    )


def _tok() -> str:
    """Query-param token suffix for static file URLs, empty when auth is off."""
    return f"?token={settings.API_TOKEN}" if settings.API_TOKEN else ""


def _serialize(p: Photo) -> dict:
    tok = _tok()
    is_vid = (p.mime_type or "").startswith("video/")
    is_large = p.file_size is not None and p.file_size >= settings.LARGE_FILE_MB * 1024 * 1024
    return {
        "id": p.id,
        "filename": p.original_filename,
        "thumbnail_url": f"/thumbnails/{Path(p.thumbnail_path).name}{tok}" if p.thumbnail_path else None,
        "preview_url": f"/previews/{Path(p.preview_path).name}{tok}" if p.preview_path else None,
        "original_url": f"/api/photos/{p.id}/original{tok}",
        "width": p.width,
        "height": p.height,
        "taken_at": p.taken_at.isoformat() if p.taken_at else None,
        "camera": f"{p.camera_make or ''} {p.camera_model or ''}".strip() or None,
        "gps": {"lat": p.gps_lat, "lon": p.gps_lon} if p.gps_lat else None,
        "tags": [{"id": t.id, "name": t.name, "source": t.source} for t in (p.tags or [])],
        "ai_tags": json.loads(p.ai_tags) if p.ai_tags else [],
        "ai_description": p.ai_description,
        "is_duplicate": p.is_duplicate,
        "is_screenshot": p.is_screenshot,
        "is_meme": not is_vid and not p.camera_make and not p.camera_model and not p.is_screenshot,
        "is_video": is_vid,
        "is_large": is_large,
        "mime_type": p.mime_type,
        "is_dark": p.is_dark,
        "is_overexposed": p.is_overexposed,
        "is_low_res": p.is_low_res,
        "burst_id": p.burst_id,
        "is_favorite": p.is_favorite,
        "quality_score": p.quality_score,
        "notes": p.notes,
        "file_size": p.file_size,
        "deleted_at": p.deleted_at.isoformat() if p.deleted_at else None,
        "created_at": p.created_at.isoformat(),
    }
