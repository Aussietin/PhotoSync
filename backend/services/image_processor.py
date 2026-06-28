from datetime import datetime
from pathlib import Path
from typing import Any


async def process_photo(file_path: Path, original_filename: str | None = None) -> dict[str, Any]:
    """Extract metadata, perceptual hash, quality score, and screenshot flag."""
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

    from services.screenshot_detector import detect_screenshot
    meta["is_screenshot"] = detect_screenshot(
        width=meta.get("width"),
        height=meta.get("height"),
        camera_make=meta.get("camera_make"),
        original_filename=original_filename or file_path.name,
    )

    return meta


def _quality_score(img, np) -> float:
    """Return a 0–1 quality score combining sharpness (blur) and exposure.

    Sharpness uses variance-of-Laplacian computed in pure numpy (no scipy).
    Both signals are measured on a fixed-size downscale so scores are
    comparable across photos of different resolutions and the calc stays fast.
    """
    QUALITY_EDGE = 512          # long-edge px the score is computed at
    SHARPNESS_CLAMP = 1000.0    # Laplacian variance considered "tack sharp"

    try:
        work = img.convert("L")
        work.thumbnail((QUALITY_EDGE, QUALITY_EDGE))
        arr = np.asarray(work, dtype="float64")

        # 4-neighbour Laplacian on the interior, vectorised (== scipy convolve
        # with [[0,1,0],[1,-4,1],[0,1,0]] minus the border).
        lap = (
            -4.0 * arr[1:-1, 1:-1]
            + arr[:-2, 1:-1] + arr[2:, 1:-1]
            + arr[1:-1, :-2] + arr[1:-1, 2:]
        )
        sharpness = min(float(lap.var()), SHARPNESS_CLAMP) / SHARPNESS_CLAMP
    except Exception:
        sharpness = 0.5

    try:
        brightness = float(arr.mean()) / 255.0
        # Penalise very dark (<0.1) or blown-out (>0.9) images
        exposure = 1.0 - abs(brightness - 0.5) * 2
    except Exception:
        exposure = 0.5

    return round(sharpness * 0.6 + exposure * 0.4, 3)


def recompute_quality(image_path) -> float | None:
    """Recompute quality score for an existing file (used by batch rescan).

    Reads the given path — pass a thumbnail for speed when rescanning a large
    library; the downscale inside _quality_score keeps results comparable.
    """
    try:
        from PIL import Image
        import numpy as np

        with Image.open(image_path) as img:
            return _quality_score(img, np)
    except Exception:
        return None


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
