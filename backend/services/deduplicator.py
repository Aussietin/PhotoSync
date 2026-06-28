from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.photo import Photo

HASH_DISTANCE_THRESHOLD = 8  # hamming distance; lower = stricter


async def find_duplicate(db: AsyncSession, phash: Optional[str]) -> Optional[int]:
    """Return the ID of an existing photo that is perceptually similar, or None."""
    if not phash:
        return None

    try:
        import imagehash

        result = await db.execute(
            select(Photo.id, Photo.perceptual_hash).where(
                Photo.perceptual_hash.is_not(None),
                Photo.is_duplicate == False,  # noqa: E712
            )
        )
        target = imagehash.hex_to_hash(phash)
        for row_id, row_hash in result.all():
            if imagehash.hex_to_hash(row_hash) - target <= HASH_DISTANCE_THRESHOLD:
                return row_id
    except Exception:
        pass

    return None
