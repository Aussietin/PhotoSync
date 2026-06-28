"""
Duplicate detection.

Two paths, for two very different scales:

1. ``find_duplicate`` — called on every single upload. Does an *exact* perceptual
   hash match via the indexed ``perceptual_hash`` column. O(log n) in the DB,
   catches identical re-saves/re-downloads instantly without an O(n) scan.

2. ``rescan_duplicates`` — a batch pass over the whole library that finds *near*
   duplicates (bursts, lightly edited copies) within a Hamming radius using an
   in-memory BK-tree. ~O(n log n) typical instead of the O(n²) of comparing
   every pair. Quality-ordered so the sharpest/best photo is kept as the
   original and the rest are flagged as duplicates of it.
"""
from typing import Optional, Callable

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.photo import Photo

HASH_DISTANCE_THRESHOLD = 8  # Hamming distance; lower = stricter


# ── BK-tree for fast Hamming-radius lookups ─────────────────────────────────────

class BKTree:
    """Burkhard-Keller tree over a discrete metric (here, Hamming distance)."""

    def __init__(self, distance: Callable):
        self._distance = distance
        self._root = None  # (item, {dist: child_node})

    def add(self, item) -> None:
        if self._root is None:
            self._root = (item, {})
            return
        node, children = self._root
        while True:
            d = self._distance(item, node)
            child = children.get(d)
            if child is None:
                children[d] = (item, {})
                return
            node, children = child

    def find(self, item, threshold: int) -> list:
        """Return all stored items within ``threshold`` of ``item``."""
        if self._root is None:
            return []
        matches: list = []
        stack = [self._root]
        while stack:
            node, children = stack.pop()
            d = self._distance(item, node)
            if d <= threshold:
                matches.append(node)
            lo, hi = d - threshold, d + threshold
            for dist_key, child in children.items():
                if lo <= dist_key <= hi:
                    stack.append(child)
        return matches


# ── Upload path: exact match only ───────────────────────────────────────────────

async def find_duplicate(db: AsyncSession, phash: Optional[str]) -> Optional[int]:
    """Return the ID of an existing photo with the *exact* same hash, or None.

    Cheap and index-backed so per-upload cost stays flat as the library grows.
    Near-duplicate detection is handled separately by ``rescan_duplicates``.
    """
    if not phash:
        return None

    result = await db.execute(
        select(Photo.id).where(
            Photo.perceptual_hash == phash,
            Photo.is_duplicate == False,  # noqa: E712
            Photo.deleted_at.is_(None),
        ).limit(1)
    )
    row = result.first()
    return row[0] if row else None


# ── Batch path: fuzzy near-duplicate rescan ─────────────────────────────────────

async def rescan_duplicates(
    db: AsyncSession,
    threshold: int = HASH_DISTANCE_THRESHOLD,
) -> dict:
    """Rebuild all duplicate relationships across the library.

    Keeps the highest-quality photo in each cluster as the original and flags
    the rest as duplicates of it. Returns summary counts.
    """
    try:
        import imagehash
    except Exception:
        return {"error": "imagehash not available", "duplicates": 0}

    # Highest quality first → that photo becomes the cluster's kept "original".
    result = await db.execute(
        select(Photo.id, Photo.perceptual_hash)
        .where(Photo.perceptual_hash.is_not(None), Photo.deleted_at.is_(None))
        .order_by(Photo.quality_score.desc().nullslast(), Photo.created_at.asc())
    )
    rows = result.all()

    tree = BKTree(distance=lambda a, b: a[1] - b[1])  # compare imagehash objects
    duplicate_of: dict[int, int] = {}   # photo_id -> original_id
    originals: set[int] = set()

    for photo_id, hash_str in rows:
        try:
            h = imagehash.hex_to_hash(hash_str)
        except Exception:
            continue
        item = (photo_id, h)
        matches = tree.find(item, threshold)
        if matches:
            # Nearest existing original (already higher quality due to ordering)
            nearest = min(matches, key=lambda m: m[1] - h)
            duplicate_of[photo_id] = nearest[0]
        else:
            originals.add(photo_id)
            tree.add(item)

    # Reset everything, then apply the new clustering in two bulk UPDATEs.
    await db.execute(
        update(Photo)
        .where(Photo.deleted_at.is_(None))
        .values(is_duplicate=False, duplicate_of_id=None)
    )

    # Group duplicates by original for compact updates
    by_original: dict[int, list[int]] = {}
    for dup_id, orig_id in duplicate_of.items():
        by_original.setdefault(orig_id, []).append(dup_id)

    for orig_id, dup_ids in by_original.items():
        await db.execute(
            update(Photo)
            .where(Photo.id.in_(dup_ids))
            .values(is_duplicate=True, duplicate_of_id=orig_id)
        )

    await db.commit()
    return {
        "scanned": len(rows),
        "originals": len(originals),
        "duplicates": len(duplicate_of),
        "groups": len(by_original),
    }
