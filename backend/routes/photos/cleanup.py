"""Trash, bulk operations, mass cleanup, undo and retention."""
import json
import logging
import os
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from starlette.background import BackgroundTask
from sqlalchemy import select, func, update, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import settings
from database import get_db
from models.photo import Photo, DeletionLog
from routes.photos.serialize import _serialize

router = APIRouter()
logger = logging.getLogger("photosync")


# ── Bulk operations ───────────────────────────────────────────────────────────

class BulkIn(BaseModel):
    photo_ids: list[int]


@router.post("/bulk/delete")
async def bulk_delete(body: BulkIn, db: AsyncSession = Depends(get_db)):
    # deleted_batch is cleared on every manual trash/restore: it marks "trashed
    # by cleanup batch X", and a stale value let 'undo X' resurrect a photo the
    # user had since restored and deliberately trashed again.
    result = await db.execute(
        update(Photo)
        .where(Photo.id.in_(body.photo_ids), Photo.deleted_at.is_(None))
        .values(deleted_at=datetime.utcnow(), deleted_batch=None)
    )
    await db.commit()
    return {"deleted": result.rowcount}


@router.post("/bulk/favorite")
async def bulk_favorite(body: BulkIn, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        update(Photo).where(Photo.id.in_(body.photo_ids)).values(is_favorite=True)
    )
    await db.commit()
    return {"favorited": result.rowcount}


@router.post("/bulk/restore")
async def bulk_restore(body: BulkIn, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        update(Photo).where(Photo.id.in_(body.photo_ids)).values(deleted_at=None, deleted_batch=None)
    )
    await db.commit()
    return {"restored": result.rowcount}


# ── Mass filter-based cleanup ───────────────────────────────────────────────────

def _meme_condition():
    """Photos with no camera EXIF that aren't screenshots — likely received/downloaded.

    iPhone originals always have a camera_make ("Apple"). Images forwarded via
    WhatsApp, Telegram, Instagram, etc. have their EXIF stripped, leaving
    camera_make NULL. Excluding already-detected screenshots avoids double-counting.
    """
    return (
        Photo.camera_make.is_(None)
        & Photo.camera_model.is_(None)
        & (Photo.is_screenshot == False)  # noqa: E712
        # Videos also lack camera EXIF here — don't mistake them for memes.
        & Photo.mime_type.not_like("video/%")
    )


def _large_condition():
    """Files at or above the configured large-file size (mostly videos)."""
    return Photo.file_size >= settings.LARGE_FILE_MB * 1024 * 1024


def _cleanup_conditions(body: "CleanupFilterIn"):
    """Build the list of OR conditions for a cleanup selection.

    Always scoped to live (non-deleted), non-favorite photos by the caller.
    Returns an empty list if no category was selected (caller should no-op).
    """
    conditions = []
    if body.screenshots:
        conditions.append(Photo.is_screenshot == True)  # noqa: E712
    if body.duplicates:
        conditions.append(Photo.is_duplicate == True)  # noqa: E712
    if body.dark:
        conditions.append(Photo.is_dark == True)  # noqa: E712
    if body.overexposed:
        conditions.append(Photo.is_overexposed == True)  # noqa: E712
    if body.low_res:
        conditions.append(Photo.is_low_res == True)  # noqa: E712
    if body.memes:
        conditions.append(_meme_condition())
    if body.large:
        conditions.append(_large_condition())
    if body.max_quality is not None:
        conditions.append(
            (Photo.quality_score <= body.max_quality) & Photo.quality_score.is_not(None)
        )
    return conditions


class CleanupFilterIn(BaseModel):
    screenshots: bool = False
    duplicates: bool = False
    dark: bool = False
    overexposed: bool = False
    low_res: bool = False
    memes: bool = False  # received/forwarded images with no camera EXIF
    large: bool = False  # big files (mostly videos) at/above LARGE_FILE_MB
    max_quality: float | None = None  # trash photos with quality <= this


@router.get("/cleanup-summary")
async def cleanup_summary(
    max_quality: float = Query(0.3, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
):
    """Counts + reclaimable space for each cleanup category. Excludes favorites."""
    live = (Photo.deleted_at.is_(None)) & (Photo.is_favorite == False)  # noqa: E712

    async def _count_and_size(extra):
        row = (await db.execute(
            select(func.count(), func.coalesce(func.sum(Photo.file_size), 0))
            .where(live & extra)
        )).first()
        return {"count": row[0], "bytes": int(row[1])}

    low_q = (Photo.quality_score <= max_quality) & Photo.quality_score.is_not(None)
    meme_cond = _meme_condition()
    large_cond = _large_condition()
    screenshots = await _count_and_size(Photo.is_screenshot == True)  # noqa: E712
    duplicates = await _count_and_size(Photo.is_duplicate == True)  # noqa: E712
    low_quality = await _count_and_size(low_q)
    dark = await _count_and_size(Photo.is_dark == True)  # noqa: E712
    overexposed = await _count_and_size(Photo.is_overexposed == True)  # noqa: E712
    low_res = await _count_and_size(Photo.is_low_res == True)  # noqa: E712
    memes = await _count_and_size(meme_cond)
    large = await _count_and_size(large_cond)
    # Union (a photo may match more than one category — count it once)
    reclaimable = await _count_and_size(
        or_(
            Photo.is_screenshot == True,  # noqa: E712
            Photo.is_duplicate == True,  # noqa: E712
            Photo.is_dark == True,  # noqa: E712
            Photo.is_overexposed == True,  # noqa: E712
            Photo.is_low_res == True,  # noqa: E712
            meme_cond,
            large_cond,
            low_q,
        )
    )

    return {
        "screenshots": screenshots,
        "duplicates": duplicates,
        "low_quality": low_quality,
        "dark": dark,
        "overexposed": overexposed,
        "low_res": low_res,
        "memes": memes,
        "large": large,
        "large_threshold_mb": settings.LARGE_FILE_MB,
        "low_quality_threshold": max_quality,
        "total_reclaimable": reclaimable,
    }


@router.post("/cleanup")
async def run_cleanup(body: CleanupFilterIn, db: AsyncSession = Depends(get_db)):
    """Send EVERY photo matching the selected categories to trash in one query.

    This is the mass-cleanup workhorse: it acts on the whole library server-side,
    not just whatever the client has loaded. Favorites are always protected.
    Each run is stamped with a batch id and logged so it can be undone.
    """
    import uuid

    conditions = _cleanup_conditions(body)
    if not conditions:
        raise HTTPException(status_code=400, detail="No cleanup category selected")

    batch = uuid.uuid4().hex
    reason = ",".join(k for k in (
        "screenshots" if body.screenshots else "",
        "duplicates" if body.duplicates else "",
        "dark" if body.dark else "",
        "overexposed" if body.overexposed else "",
        "low_res" if body.low_res else "",
        "memes" if body.memes else "",
        "large" if body.large else "",
        "low_quality" if body.max_quality is not None else "",
    ) if k) or "manual"

    result = await db.execute(
        update(Photo)
        .where(
            Photo.deleted_at.is_(None),
            Photo.is_favorite == False,  # noqa: E712
            or_(*conditions),
        )
        .values(deleted_at=datetime.utcnow(), deleted_batch=batch)
    )
    count = result.rowcount
    if count:
        db.add(DeletionLog(batch=batch, reason=reason, count=count))
    await db.commit()
    return {"deleted": count, "batch": batch}


# ── Undo / audit / retention ────────────────────────────────────────────────────

@router.get("/cleanup-history")
async def cleanup_history(db: AsyncSession = Depends(get_db)):
    logs = (await db.execute(
        select(DeletionLog).order_by(DeletionLog.created_at.desc()).limit(50)
    )).scalars().all()
    return {"history": [{
        "batch": l.batch,
        "reason": l.reason,
        "count": l.count,
        "undone": l.undone,
        "created_at": l.created_at.isoformat(),
    } for l in logs]}


@router.post("/undo-cleanup/{batch}")
async def undo_cleanup(batch: str, db: AsyncSession = Depends(get_db)):
    """Restore every photo trashed in a given cleanup batch."""
    log = (await db.execute(
        select(DeletionLog).where(DeletionLog.batch == batch)
    )).scalar_one_or_none()
    if log is None:
        raise HTTPException(status_code=404, detail="Batch not found")
    result = await db.execute(
        update(Photo)
        .where(Photo.deleted_batch == batch, Photo.deleted_at.is_not(None))
        .values(deleted_at=None, deleted_batch=None)
    )
    await db.execute(
        update(DeletionLog).where(DeletionLog.batch == batch).values(undone=True)
    )
    await db.commit()
    return {"restored": result.rowcount, "batch": batch}


def _under_uploads(path: str) -> bool:
    """True if a file lives inside PhotoSync's own uploads dir — i.e. a copy we
    made — as opposed to an in-place folder-import original we must never delete."""
    try:
        return Path(path).resolve().is_relative_to(Path(settings.UPLOAD_DIR).resolve())
    except (ValueError, OSError):
        return False


def _remove_photo_files(photo: Photo) -> None:
    """Delete a photo's on-disk files when permanently removing it.

    Thumbnails and previews are always PhotoSync-generated, so they're safe to
    remove. The *original* is only deleted when it's a copy we made (under
    uploads/) — or when DELETE_IN_PLACE_ORIGINALS is explicitly enabled. This
    protects folder-imported source files (often the user's only copy) from
    being destroyed by emptying Trash.
    """
    paths = [photo.thumbnail_path, photo.preview_path]
    if photo.file_path and (settings.DELETE_IN_PLACE_ORIGINALS or _under_uploads(photo.file_path)):
        paths.append(photo.file_path)
    for path in paths:
        if path:
            try:
                os.remove(path)
            except FileNotFoundError:
                pass


@router.post("/empty-trash")
async def empty_trash(
    older_than_days: int | None = Query(None, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Permanently delete trashed photos (optionally only those older than N days).

    Removes PhotoSync-managed files (thumbnail, preview, and uploaded copies) then
    the DB rows. In-place folder-import originals are preserved unless
    DELETE_IN_PLACE_ORIGINALS is set (see config) — so this can never wipe an
    un-backed-up source library.
    """
    q = select(Photo).where(Photo.deleted_at.is_not(None))
    if older_than_days is not None:
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=older_than_days)
        q = q.where(Photo.deleted_at <= cutoff)

    photos = (await db.execute(q)).scalars().all()
    removed = 0
    for photo in photos:
        _remove_photo_files(photo)
        await db.delete(photo)
        removed += 1
    await db.commit()
    return {"permanently_deleted": removed}


def _retention_cutoff() -> datetime:
    from datetime import timedelta
    return datetime.utcnow() - timedelta(days=settings.TRASH_RETENTION_DAYS)


@router.get("/trash-status")
async def trash_status(db: AsyncSession = Depends(get_db)):
    """Retention policy + how much of Trash the auto-sweep would clear.

    `expired` is the count/bytes of trashed photos already older than
    TRASH_RETENTION_DAYS — i.e. what the next startup sweep removes when
    TRASH_AUTO_EMPTY is on.
    """
    cutoff = _retention_cutoff()

    async def _count_and_size(extra):
        row = (await db.execute(
            select(func.count(), func.coalesce(func.sum(Photo.file_size), 0))
            .where(Photo.deleted_at.is_not(None), extra)
        )).first()
        return {"count": row[0], "bytes": int(row[1])}

    total = await _count_and_size(Photo.deleted_at.is_not(None))
    expired = await _count_and_size(Photo.deleted_at <= cutoff)
    oldest = (await db.execute(
        select(func.min(Photo.deleted_at)).where(Photo.deleted_at.is_not(None))
    )).scalar()

    return {
        "auto_empty_enabled": settings.TRASH_AUTO_EMPTY,
        "retention_days": settings.TRASH_RETENTION_DAYS,
        "in_trash": total,
        "expired": expired,
        "oldest_deleted_at": oldest.isoformat() if oldest else None,
    }


async def sweep_expired_trash() -> int:
    """Permanently delete trashed photos older than TRASH_RETENTION_DAYS.

    No-op unless TRASH_AUTO_EMPTY is set. Called once at startup (see app.py
    lifespan). Uses the same file-removal rules as empty-trash, so in-place
    folder-import originals are preserved unless DELETE_IN_PLACE_ORIGINALS is on.

    Looks up database.AsyncSessionLocal dynamically (not by name-import) so tests
    can redirect it to an isolated in-memory DB — same pattern as services.jobs.
    """
    if not settings.TRASH_AUTO_EMPTY:
        return 0

    import database

    cutoff = _retention_cutoff()
    removed = 0
    async with database.AsyncSessionLocal() as db:
        photos = (await db.execute(
            select(Photo).where(
                Photo.deleted_at.is_not(None), Photo.deleted_at <= cutoff
            )
        )).scalars().all()
        for photo in photos:
            _remove_photo_files(photo)
            await db.delete(photo)
            removed += 1
        await db.commit()

    if removed:
        logger.info(
            "trash retention sweep: permanently removed %d photo(s) older than %d days",
            removed, settings.TRASH_RETENTION_DAYS,
        )
    return removed
