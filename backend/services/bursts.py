"""
Burst grouping.

iPhones produce runs of near-identical frames (burst mode, or just several taps).
We group photos taken within a short time window that are also visually similar,
so the UI can offer "keep the best, cull the rest". A burst is only recorded when
2+ photos cluster together.
"""
import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.photo import Photo

BURST_WINDOW_SECONDS = 10
BURST_HASH_THRESHOLD = 14  # looser than exact-dup; bursts have more variation


async def group_bursts(db: AsyncSession) -> dict:
    """Recompute burst_id across the library. Returns summary counts."""
    try:
        import imagehash
    except Exception:
        return {"bursts": 0, "photos_in_bursts": 0}

    rows = (await db.execute(
        select(Photo.id, Photo.taken_at, Photo.perceptual_hash)
        .where(
            Photo.deleted_at.is_(None),
            Photo.taken_at.is_not(None),
            Photo.perceptual_hash.is_not(None),
        )
        .order_by(Photo.taken_at.asc())
    )).all()

    # Reset existing burst assignments in scope.
    await db.execute(
        update(Photo).where(Photo.deleted_at.is_(None)).values(burst_id=None)
    )

    clusters: list[list[int]] = []
    current: list[int] = []
    prev_time = None
    prev_hash = None

    for photo_id, taken_at, hash_str in rows:
        try:
            h = imagehash.hex_to_hash(hash_str)
        except Exception:
            continue

        close_in_time = (
            prev_time is not None
            and (taken_at - prev_time).total_seconds() <= BURST_WINDOW_SECONDS
        )
        similar = prev_hash is not None and (h - prev_hash) <= BURST_HASH_THRESHOLD

        if close_in_time and similar:
            current.append(photo_id)
        else:
            if len(current) >= 2:
                clusters.append(current)
            current = [photo_id]

        prev_time, prev_hash = taken_at, h

    if len(current) >= 2:
        clusters.append(current)

    photos_in_bursts = 0
    for cluster in clusters:
        burst_id = uuid.uuid4().hex
        await db.execute(
            update(Photo).where(Photo.id.in_(cluster)).values(burst_id=burst_id)
        )
        photos_in_bursts += len(cluster)

    await db.commit()
    return {"bursts": len(clusters), "photos_in_bursts": photos_in_bursts}
