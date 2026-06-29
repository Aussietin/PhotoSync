"""
AI tagging service — pluggable backend.

When OPENAI_API_KEY is configured in settings, uses GPT-4o-mini Vision to
generate descriptive tags and a one-sentence description for each photo.
Falls back to a color-heuristic tagger if no key is set or on any API error.
"""
import base64
import json
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.photo import Photo, Tag


async def tag_photo(db: AsyncSession, photo: Photo) -> list[str]:
    """Generate AI tags for a photo and persist them. Returns the tag list."""
    # Prefer the thumbnail (already small JPEG) to minimise API payload.
    image_path = _resolve_image(photo)
    if image_path is None:
        return []

    if settings.OPENAI_API_KEY:
        tags, description = await _tag_with_openai(image_path)
    else:
        tags = await _tag_with_heuristics(image_path)
        description = None

    if not tags:
        return []

    photo.ai_tags = json.dumps(tags)
    if description:
        photo.ai_description = description

    # Replace any previous AI-generated tags for this photo.
    # Use a direct query instead of the relationship to avoid async lazy-load.
    from sqlalchemy import select
    old_tags = (await db.execute(
        select(Tag).where(Tag.photo_id == photo.id, Tag.source == "ai")
    )).scalars().all()
    for t in old_tags:
        await db.delete(t)

    confidence = 0.9 if settings.OPENAI_API_KEY else 0.8
    for name in tags:
        db.add(Tag(photo_id=photo.id, name=name, source="ai", confidence=confidence))

    await db.commit()
    return tags


def _resolve_image(photo: Photo) -> Path | None:
    """Return the best available image path for a photo (thumbnail preferred)."""
    for candidate in (photo.thumbnail_path, photo.file_path):
        if candidate:
            p = Path(candidate)
            if p.exists():
                return p
    return None


async def _tag_with_openai(image_path: Path) -> tuple[list[str], str | None]:
    """Call GPT-4o-mini Vision API and return (tags, description)."""
    import httpx

    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    mime = mime_map.get(image_path.suffix.lower(), "image/jpeg")

    try:
        with open(image_path, "rb") as fh:
            image_b64 = base64.b64encode(fh.read()).decode()

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{mime};base64,{image_b64}",
                                        "detail": "low",
                                    },
                                },
                                {
                                    "type": "text",
                                    "text": (
                                        "Analyze this photo and return a JSON object with two keys:\n"
                                        '- "tags": array of 5-10 lowercase descriptive tags '
                                        "(scene, subjects, mood, colours, activity; 1-3 words each)\n"
                                        '- "description": one concise sentence describing the photo'
                                    ),
                                },
                            ],
                        }
                    ],
                    "max_tokens": 200,
                    "response_format": {"type": "json_object"},
                },
                timeout=30.0,
            )
        resp.raise_for_status()
        content = json.loads(resp.json()["choices"][0]["message"]["content"])
        tags = [str(t).lower().strip() for t in content.get("tags", []) if t][:15]
        description = content.get("description") or None
        return tags, description

    except Exception:
        return [], None


async def _tag_with_heuristics(file_path: Path) -> list[str]:
    """Colour-based fallback tagger — no external dependencies beyond Pillow/numpy."""
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
