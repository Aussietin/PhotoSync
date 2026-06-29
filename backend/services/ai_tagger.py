"""
AI tagging service — fully local, no external API.

When the local CLIP model is available (pip install -r requirements-ai.txt) this
computes an on-device image embedding and derives zero-shot tags from it. The
embedding is also stored on the photo so semantic search is instant. If the
model isn't installed it falls back to a colour heuristic so the feature still
produces *something* and never blocks. Nothing is ever sent off the machine.
"""
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.photo import Photo, Tag
from services import embeddings


async def tag_photo(db: AsyncSession, photo: Photo) -> list[str]:
    """Generate AI tags for a photo (and its CLIP embedding) and persist them."""
    image_path = _resolve_image(photo)
    if image_path is None:
        return []

    vec = embeddings.embed_image(image_path)
    if vec is not None:
        photo.clip_embedding = embeddings.to_blob(vec)
        tags = embeddings.zero_shot_tags(vec)
        confidence = 0.9
    else:
        tags = await _tag_with_heuristics(image_path)
        confidence = 0.5

    if not tags:
        return []

    photo.ai_tags = json.dumps(tags)

    # Replace any previous AI-generated tags for this photo. Query directly
    # rather than touching the relationship to avoid an async lazy-load.
    old_tags = (await db.execute(
        select(Tag).where(Tag.photo_id == photo.id, Tag.source == "ai")
    )).scalars().all()
    for t in old_tags:
        await db.delete(t)

    for name in tags:
        db.add(Tag(photo_id=photo.id, name=name, source="ai", confidence=confidence))

    await db.commit()
    return tags


def _resolve_image(photo: Photo) -> Path | None:
    """Best available image path for a photo — prefer the small thumbnail."""
    for candidate in (photo.thumbnail_path, photo.file_path):
        if candidate:
            p = Path(candidate)
            if p.exists():
                return p
    return None


async def _tag_with_heuristics(file_path: Path) -> list[str]:
    """Colour-based fallback tagger — Pillow/numpy only, no model needed."""
    tags: list[str] = []
    try:
        from PIL import Image
        import numpy as np

        img = Image.open(file_path).convert("RGB").resize((64, 64))
        arr = np.array(img, dtype=float)
        r, g, b = arr.mean(axis=(0, 1))

        if b > r and b > g:
            tags.append("blue tones")
        elif g > r and g > b:
            tags.append("green scene")
        elif r > g and r > b:
            tags.append("warm tones")
        else:
            tags.append("neutral")

        brightness = arr.mean()
        if brightness > 180:
            tags.append("bright")
        elif brightness < 80:
            tags.append("dark")

    except Exception:
        pass

    return tags
