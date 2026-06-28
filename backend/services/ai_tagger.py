"""
AI tagging service — pluggable backend.

Currently uses a simple heuristic (dominant color + basic scene keywords).
Swap out `_tag_with_heuristics` for a real model call (CLIP, AWS Rekognition,
Google Vision, etc.) without changing the public interface.
"""
import json
from pathlib import Path
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from models.photo import Photo, Tag


async def tag_photo(db: AsyncSession, photo: Photo) -> list[str]:
    """Generate AI tags for a photo and persist them."""
    tags = await _tag_with_heuristics(Path(photo.file_path))
    if not tags:
        return []

    photo.ai_tags = json.dumps(tags)
    for name in tags:
        db.add(Tag(photo_id=photo.id, name=name, source="ai", confidence=0.8))

    await db.commit()
    return tags


async def _tag_with_heuristics(file_path: Path) -> list[str]:
    """Placeholder: returns color-based tags. Replace with real AI model."""
    tags: list[str] = []
    try:
        from PIL import Image
        import numpy as np

        img = Image.open(file_path).convert("RGB").resize((64, 64))
        arr = np.array(img)
        avg = arr.mean(axis=(0, 1))
        r, g, b = avg

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
