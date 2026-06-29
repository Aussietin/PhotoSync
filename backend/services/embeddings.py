"""
Local CLIP embeddings — semantic search + zero-shot tagging, fully on-device.

Uses sentence-transformers' ``clip-ViT-B-32`` model run on CPU. No image or
query text ever leaves the machine; there is no API and no cost.

The model is an OPTIONAL dependency. If sentence-transformers / torch aren't
installed (or the weights can't load), every public function degrades safely:
``embed_image`` / ``embed_text`` return ``None`` and callers fall back to the
colour heuristic. This keeps the core app and the test suite light — install
the model only when you want real AI:  ``pip install -r requirements-ai.txt``.

Vectors are L2-normalised, so cosine similarity is a plain dot product.
"""
from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Optional

import numpy as np

from config import settings

logger = logging.getLogger("photosync")

# Lazily-loaded singleton model. _load_failed latches so we don't retry a slow
# import on every call once it's known to be unavailable.
_model = None
_model_lock = threading.Lock()
_load_failed = False

# Cache of label-set -> (labels, text-embedding matrix) for zero-shot tagging.
_label_cache: dict[tuple[str, ...], tuple[list[str], np.ndarray]] = {}

# Candidate labels for zero-shot categorisation. Tuned for phone-camera cleanup:
# the categories someone actually triages by. The display tag is derived by
# stripping the leading article (see _label_to_tag).
CANDIDATE_LABELS: list[str] = [
    "a screenshot", "a receipt", "a document", "a meme", "a chart or graph",
    "text on a screen", "a selfie", "a portrait of a person", "a group of people",
    "food", "a restaurant meal", "a drink", "a dog", "a cat", "a pet",
    "a landscape", "a beach", "mountains", "a forest", "a sunset", "the night sky",
    "a city street", "a building", "indoors", "outdoors", "a car", "a flower",
    "a plant", "water", "snow", "a concert or event", "artwork", "a product photo",
    "a baby", "a wedding", "sports", "a map", "a QR code or barcode",
]


def is_available() -> bool:
    """True if the local CLIP model loaded successfully."""
    return _get_model() is not None


def _get_model():
    """Load (once) and return the CLIP model, or None if unavailable."""
    global _model, _load_failed
    if _model is not None or _load_failed:
        return _model
    with _model_lock:
        if _model is not None or _load_failed:
            return _model
        try:
            from sentence_transformers import SentenceTransformer

            _model = SentenceTransformer(settings.CLIP_MODEL)
        except Exception as exc:
            # Soft dependency: AI features stay off if torch/sentence-transformers
            # aren't installed or the weights can't load. Logged once (latched).
            logger.warning(
                "Local CLIP model unavailable — semantic search and AI tagging "
                "disabled (install requirements-ai.txt to enable): %s", exc
            )
            _load_failed = True
            _model = None
        return _model


def embed_image(path: Path) -> Optional[np.ndarray]:
    """Return the L2-normalised CLIP embedding for an image, or None."""
    model = _get_model()
    if model is None:
        return None
    try:
        from PIL import Image

        with Image.open(path) as img:
            rgb = img.convert("RGB")
            vec = model.encode([rgb], convert_to_numpy=True, normalize_embeddings=True)[0]
        return vec.astype(np.float32)
    except Exception as exc:
        logger.warning("Could not embed image %s: %s", path, exc)
        return None


def embed_text(text: str) -> Optional[np.ndarray]:
    """Return the L2-normalised CLIP embedding for a text query, or None."""
    model = _get_model()
    if model is None:
        return None
    try:
        vec = model.encode([text], convert_to_numpy=True, normalize_embeddings=True)[0]
        return vec.astype(np.float32)
    except Exception as exc:
        logger.warning("Could not embed query text: %s", exc)
        return None


def _label_to_tag(label: str) -> str:
    """'a dog' -> 'dog', 'the night sky' -> 'night sky'."""
    for article in ("a ", "an ", "the "):
        if label.startswith(article):
            return label[len(article):]
    return label


def _label_embeddings(labels: tuple[str, ...]) -> Optional[tuple[list[str], np.ndarray]]:
    """Return (display_tags, embedding_matrix) for a label set, cached."""
    if labels in _label_cache:
        return _label_cache[labels]
    model = _get_model()
    if model is None:
        return None
    try:
        mat = model.encode(list(labels), convert_to_numpy=True, normalize_embeddings=True)
    except Exception:
        return None
    tags = [_label_to_tag(l) for l in labels]
    result = (tags, mat.astype(np.float32))
    _label_cache[labels] = result
    return result


def zero_shot_tags(
    image_vec: np.ndarray,
    labels: Optional[list[str]] = None,
    threshold: Optional[float] = None,
    max_tags: Optional[int] = None,
) -> list[str]:
    """Score an image embedding against candidate labels; return matching tags.

    Tags are returned highest-similarity first, keeping those above ``threshold``
    up to ``max_tags``. Returns [] if the label embeddings can't be computed.
    """
    labels = labels or CANDIDATE_LABELS
    threshold = settings.AI_TAG_THRESHOLD if threshold is None else threshold
    max_tags = settings.AI_MAX_TAGS if max_tags is None else max_tags

    le = _label_embeddings(tuple(labels))
    if le is None:
        return []
    tags, mat = le
    scores = mat @ np.asarray(image_vec, dtype=np.float32)
    order = np.argsort(scores)[::-1]
    out = [tags[i] for i in order if scores[i] >= threshold]
    return out[:max_tags]


# ── (De)serialisation for DB storage ────────────────────────────────────────

def to_blob(vec: np.ndarray) -> bytes:
    """Pack a float32 vector to raw bytes for the clip_embedding column."""
    return np.asarray(vec, dtype=np.float32).tobytes()


def from_blob(blob: bytes) -> np.ndarray:
    """Unpack raw bytes back to a float32 vector."""
    return np.frombuffer(blob, dtype=np.float32)


def rank_by_similarity(query_vec: np.ndarray, blobs: list[bytes]) -> np.ndarray:
    """Cosine similarity of a query vector against a list of stored embeddings.

    Embeddings are already normalised, so this is a matrix-vector dot product —
    a few milliseconds even for tens of thousands of photos. Returns a 1-D array
    of scores aligned with ``blobs``.
    """
    if not blobs:
        return np.empty(0, dtype=np.float32)
    mat = np.vstack([from_blob(b) for b in blobs])
    return mat @ np.asarray(query_vec, dtype=np.float32)
