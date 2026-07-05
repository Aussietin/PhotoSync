"""
Local face recognition — detect, embed, and cluster faces fully on-device.

Wraps InsightFace (ArcFace, ONNX Runtime, CPU) as an OPTIONAL dependency, the
same way services/embeddings.py wraps CLIP. If insightface/onnxruntime aren't
installed (or the model can't load) every public call degrades to "no faces"
and the rest of the app keeps working. Nothing ever leaves the machine.

Embeddings are L2-normalised (``normed_embedding``), so cosine similarity is a
plain dot product and clustering is cheap.
"""
from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Optional

import numpy as np

from config import settings
from services import heif_support  # noqa: F401 — HEIC opener so iPhone files load

logger = logging.getLogger("photosync")

_app = None
_app_lock = threading.Lock()
_load_failed = False


def is_available() -> bool:
    """True if the local face model loaded successfully."""
    return _get_app() is not None


def _get_app():
    """Load (once) and return the InsightFace app, or None if unavailable."""
    global _app, _load_failed
    if _app is not None or _load_failed:
        return _app
    with _app_lock:
        if _app is not None or _load_failed:
            return _app
        try:
            from insightface.app import FaceAnalysis

            app = FaceAnalysis(
                name=settings.FACE_MODEL,
                allowed_modules=["detection", "recognition"],
                providers=["CPUExecutionProvider"],
            )
            app.prepare(ctx_id=-1, det_size=(640, 640))  # ctx_id=-1 → CPU
            _app = app
        except Exception as exc:
            logger.warning(
                "Local face model unavailable — face grouping disabled "
                "(install requirements-ai.txt to enable): %s", exc
            )
            _load_failed = True
            _app = None
        return _app


def _load_bgr(path: Path) -> Optional[np.ndarray]:
    """Read an image (incl. HEIC) as a contiguous BGR uint8 array for InsightFace."""
    try:
        from PIL import Image, ImageOps

        with Image.open(path) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            rgb = np.asarray(im)
        return np.ascontiguousarray(rgb[:, :, ::-1])  # RGB → BGR
    except Exception as exc:
        logger.warning("Could not read %s for face detection: %s", path, exc)
        return None


def detect_faces(path: Path) -> list[dict]:
    """Detect faces in an image. Returns a list of dicts:
    ``{embedding: float32[512] (normalised), bbox: (x,y,w,h), det_score: float}``.

    Filters out weak detections and tiny faces. Empty list if the model is
    unavailable or the image has no usable faces.
    """
    app = _get_app()
    if app is None:
        return []
    img = _load_bgr(path)
    if img is None:
        return []
    try:
        detected = app.get(img)
    except Exception as exc:
        logger.warning("Face detection failed on %s: %s", path, exc)
        return []

    out: list[dict] = []
    for f in detected:
        score = float(getattr(f, "det_score", 0.0) or 0.0)
        if score < settings.FACE_MIN_DET_SCORE:
            continue
        x1, y1, x2, y2 = (int(v) for v in f.bbox)
        w, h = max(0, x2 - x1), max(0, y2 - y1)
        if max(w, h) < settings.FACE_MIN_SIZE:
            continue
        vec = getattr(f, "normed_embedding", None)
        if vec is None:
            continue
        out.append({
            "embedding": np.asarray(vec, dtype=np.float32),
            "bbox": (max(0, x1), max(0, y1), w, h),
            "det_score": score,
        })
    return out


def save_face_crop(image_path: Path, bbox: tuple[int, int, int, int], out_path: Path,
                   margin: float = 0.35, size: int = 160) -> Optional[Path]:
    """Crop a face (with margin) to a small square JPEG used as the person thumb."""
    try:
        from PIL import Image, ImageOps

        x, y, w, h = bbox
        with Image.open(image_path) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            mx, my = int(w * margin), int(h * margin)
            box = (max(0, x - mx), max(0, y - my),
                   min(im.width, x + w + mx), min(im.height, y + h + my))
            crop = im.crop(box)
            crop.thumbnail((size, size), Image.LANCZOS)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            crop.save(out_path, "JPEG", quality=85)
        return out_path
    except Exception as exc:
        logger.warning("Could not crop face from %s: %s", image_path, exc)
        return None


# ── Embedding (de)serialisation + clustering ────────────────────────────────────

def to_blob(vec: np.ndarray) -> bytes:
    return np.asarray(vec, dtype=np.float32).tobytes()


def from_blob(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)


def best_match(vec: np.ndarray, centroids: list[tuple[int, np.ndarray]],
               threshold: Optional[float] = None) -> Optional[int]:
    """Return the person id whose centroid is closest to ``vec`` above threshold.

    ``centroids`` is a list of (person_id, centroid_vector). Cosine similarity =
    dot product (vectors are normalised). Returns None to start a new cluster.
    """
    if not centroids:
        return None
    threshold = settings.FACE_MATCH_THRESHOLD if threshold is None else threshold
    v = np.asarray(vec, dtype=np.float32)
    best_id, best_sim = None, threshold
    for pid, c in centroids:
        sim = float(np.dot(v, c))
        if sim >= best_sim:
            best_id, best_sim = pid, sim
    return best_id


def updated_centroid(old: Optional[np.ndarray], count: int, vec: np.ndarray) -> np.ndarray:
    """Running mean of member embeddings, re-normalised so cosine stays a dot product."""
    v = np.asarray(vec, dtype=np.float32)
    mean = v if old is None or count <= 0 else (old * count + v) / (count + 1)
    norm = np.linalg.norm(mean)
    return (mean / norm).astype(np.float32) if norm else mean.astype(np.float32)
