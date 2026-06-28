from datetime import datetime
from pathlib import Path
from typing import Any


async def process_photo(file_path: Path) -> dict[str, Any]:
    """Extract metadata, perceptual hash, and quality score from an image."""
    meta: dict[str, Any] = {}

    try:
        from PIL import Image
        import imagehash
        import numpy as np

        img = Image.open(file_path)
        meta["width"], meta["height"] = img.size
        meta["perceptual_hash"] = str(imagehash.phash(img))
        meta["quality_score"] = _quality_score(img, np)
    except Exception:
        pass

    meta.update(_extract_exif(file_path))
    return meta


def _quality_score(img, np) -> float:
    """Return a 0–1 quality score combining sharpness and exposure."""
    try:
        gray = img.convert("L")
        arr = np.array(gray, dtype=float)

        # Laplacian variance → sharpness (clamp at 800 for normalisation)
        laplacian = np.array([
            [0, 1, 0],
            [1, -4, 1],
            [0, 1, 0],
        ])
        from scipy.ndimage import convolve
        lap = convolve(arr, laplacian)
        sharpness = min(float(np.var(lap)), 800.0) / 800.0
    except Exception:
        # scipy not available — skip sharpness, use brightness only
        sharpness = 0.5

    try:
        rgb = img.convert("RGB")
        brightness = float(np.array(rgb).mean()) / 255.0
        # Penalise very dark (<0.1) or very bright (>0.9) images
        exposure = 1.0 - abs(brightness - 0.5) * 2
    except Exception:
        exposure = 0.5

    return round(sharpness * 0.6 + exposure * 0.4, 3)


def _extract_exif(file_path: Path) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    try:
        import exifread

        with open(file_path, "rb") as f:
            tags = exifread.process_file(f, stop_tag="GPS GPSLongitude", details=False)

        if dt_tag := tags.get("EXIF DateTimeOriginal"):
            try:
                meta["taken_at"] = datetime.strptime(str(dt_tag), "%Y:%m:%d %H:%M:%S")
            except ValueError:
                pass

        meta["camera_make"] = str(tags["Image Make"]) if "Image Make" in tags else None
        meta["camera_model"] = str(tags["Image Model"]) if "Image Model" in tags else None

        lat = _gps_to_decimal(tags, "GPS GPSLatitude", "GPS GPSLatitudeRef")
        lon = _gps_to_decimal(tags, "GPS GPSLongitude", "GPS GPSLongitudeRef")
        if lat is not None:
            meta["gps_lat"] = lat
        if lon is not None:
            meta["gps_lon"] = lon

    except Exception:
        pass

    return meta


def _gps_to_decimal(tags: dict, coord_key: str, ref_key: str):
    try:
        coord = tags[coord_key].values
        ref = str(tags[ref_key])
        degrees = float(coord[0].num) / float(coord[0].den)
        minutes = float(coord[1].num) / float(coord[1].den)
        seconds = float(coord[2].num) / float(coord[2].den)
        decimal = degrees + minutes / 60 + seconds / 3600
        if ref in ("S", "W"):
            decimal = -decimal
        return decimal
    except Exception:
        return None
