from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".gif", ".tiff", ".tif"}
# iPhone records video as HEVC .mov; .mp4/.m4v cover most other sources.
VIDEO_EXTENSIONS = {".mov", ".mp4", ".m4v", ".avi", ".hevc", ".3gp", ".mkv", ".webm"}
MEDIA_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS

_MIME_BY_EXT = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".heic": "image/heic", ".heif": "image/heif", ".webp": "image/webp",
    ".gif": "image/gif", ".tiff": "image/tiff", ".tif": "image/tiff",
    ".mov": "video/quicktime", ".mp4": "video/mp4", ".m4v": "video/x-m4v",
    ".avi": "video/x-msvideo", ".hevc": "video/hevc", ".3gp": "video/3gpp",
    ".mkv": "video/x-matroska", ".webm": "video/webm",
}


def is_image(filename: str) -> bool:
    return Path(filename).suffix.lower() in IMAGE_EXTENSIONS


def is_video(filename: str) -> bool:
    return Path(filename).suffix.lower() in VIDEO_EXTENSIONS


def is_media(filename: str) -> bool:
    """Images *and* videos — the full set PhotoSync will ingest."""
    return Path(filename).suffix.lower() in MEDIA_EXTENSIONS


def guess_mime(filename: str) -> str:
    return _MIME_BY_EXT.get(Path(filename).suffix.lower(), "application/octet-stream")


def human_size(bytes_: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if bytes_ < 1024:
            return f"{bytes_:.1f} {unit}"
        bytes_ /= 1024
    return f"{bytes_:.1f} TB"
