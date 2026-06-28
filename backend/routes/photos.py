import io
import json
import os
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, func, update, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from models.photo import Photo, DeletionLog
from services.storage import save_upload
from services.image_processor import process_photo
from services.deduplicator import find_duplicate
from utils.helpers import is_image

router = APIRouter()

SORT_MAP = {
    "date_desc": Photo.taken_at.desc().nullslast(),
    "date_asc": Photo.taken_at.asc().nullsfirst(),
    "size_desc": Photo.file_size.desc(),
    "size_asc": Photo.file_size.asc(),
    "quality_desc": Photo.quality_score.desc().nullslast(),
    "name_asc": Photo.original_filename.asc(),
    "name_desc": Photo.original_filename.desc(),
    "created_desc": Photo.created_at.desc(),
}


# ── Upload ────────────────────────────────────────────────────────────────────

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_photos(
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    results = []
    for file in files:
        orig_name = file.filename or "photo.jpg"
        file_path, thumb_path, preview_path, file_size = await save_upload(file)
        metadata = await process_photo(file_path, original_filename=orig_name)

        dup_id = await find_duplicate(db, metadata.get("perceptual_hash"))

        photo = Photo(
            filename=file_path.name,
            original_filename=orig_name,
            file_path=str(file_path),
            thumbnail_path=str(thumb_path) if thumb_path else None,
            preview_path=str(preview_path) if preview_path else None,
            file_size=file_size,
            mime_type=file.content_type or "image/jpeg",
            is_duplicate=dup_id is not None,
            duplicate_of_id=dup_id,
            **_photo_fields(metadata),
        )
        db.add(photo)
        await db.commit()
        await db.refresh(photo)
        results.append({"id": photo.id, "filename": photo.original_filename, "is_duplicate": photo.is_duplicate})

    return {"uploaded": len(results), "photos": results}


def _photo_fields(metadata: dict) -> dict:
    """Map processor metadata to Photo column kwargs shared by upload/import."""
    return dict(
        width=metadata.get("width"),
        height=metadata.get("height"),
        taken_at=metadata.get("taken_at"),
        camera_make=metadata.get("camera_make"),
        camera_model=metadata.get("camera_model"),
        gps_lat=metadata.get("gps_lat"),
        gps_lon=metadata.get("gps_lon"),
        perceptual_hash=metadata.get("perceptual_hash"),
        quality_score=metadata.get("quality_score"),
        is_screenshot=metadata.get("is_screenshot", False),
        is_dark=metadata.get("is_dark", False),
        is_overexposed=metadata.get("is_overexposed", False),
        is_low_res=metadata.get("is_low_res", False),
    )


# ── Folder import ─────────────────────────────────────────────────────────────

class FolderImportIn(BaseModel):
    path: str
    recursive: bool = True


@router.post("/import-folder", status_code=status.HTTP_202_ACCEPTED)
async def import_folder(body: FolderImportIn):
    """Kick off a background import job. Poll GET /api/jobs/{id} for progress."""
    folder = Path(body.path)
    if not folder.exists() or not folder.is_dir():
        raise HTTPException(status_code=400, detail="Path does not exist or is not a directory")

    pattern = "**/*" if body.recursive else "*"
    files = [p for p in folder.glob(pattern) if p.is_file() and is_image(p.name)]

    async def runner(session: AsyncSession, job) -> dict:
        from services.storage import _make_thumbnail, _make_preview
        from services.deduplicator import rescan_duplicates
        import uuid

        job.total = len(files)
        await session.commit()

        known = set((await session.execute(select(Photo.file_path))).scalars().all())
        imported, skipped = 0, 0

        for idx, file_path in enumerate(files):
            if str(file_path) not in known:
                metadata = await process_photo(file_path, original_filename=file_path.name)
                stem = uuid.uuid4().hex
                thumb_path = await _make_thumbnail(file_path, stem)
                preview_path = await _make_preview(file_path, stem)
                session.add(Photo(
                    filename=file_path.name,
                    original_filename=file_path.name,
                    file_path=str(file_path),
                    thumbnail_path=str(thumb_path) if thumb_path else None,
                    preview_path=str(preview_path) if preview_path else None,
                    file_size=file_path.stat().st_size,
                    mime_type="image/jpeg",
                    **_photo_fields(metadata),
                ))
                known.add(str(file_path))
                imported += 1
            else:
                skipped += 1

            # Commit + report progress in batches to keep the UI moving.
            if (idx + 1) % 50 == 0 or idx + 1 == len(files):
                job.processed = idx + 1
                await session.commit()

        dup_summary = await rescan_duplicates(session) if imported else {"duplicates": 0}
        return {"imported": imported, "skipped": skipped,
                "duplicates_found": dup_summary.get("duplicates", 0)}

    from services.jobs import start_job
    job_id = await start_job("import", runner, total=len(files))
    return {"job_id": job_id, "files_found": len(files)}


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("")
async def list_photos(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    include_duplicates: bool = Query(False),
    favorites_only: bool = Query(False),
    sort: str = Query("date_desc"),
    db: AsyncSession = Depends(get_db),
):
    order = SORT_MAP.get(sort, Photo.taken_at.desc().nullslast())
    offset = (page - 1) * per_page

    q = select(Photo).where(Photo.deleted_at.is_(None))
    if not include_duplicates:
        q = q.where(Photo.is_duplicate == False)  # noqa: E712
    if favorites_only:
        q = q.where(Photo.is_favorite == True)  # noqa: E712

    count_q = q.with_only_columns(func.count()).order_by(None)
    total = (await db.execute(count_q)).scalar_one()

    q = q.options(selectinload(Photo.tags)).order_by(order).offset(offset).limit(per_page)
    result = await db.execute(q)
    photos = result.scalars().all()

    return {"total": total, "page": page, "per_page": per_page, "photos": [_serialize(p) for p in photos]}


# ── Timeline ──────────────────────────────────────────────────────────────────

@router.get("/timeline")
async def timeline(db: AsyncSession = Depends(get_db)):
    q = (
        select(Photo)
        .where(Photo.taken_at.is_not(None), Photo.is_duplicate == False, Photo.deleted_at.is_(None))  # noqa: E712
        .options(selectinload(Photo.tags))
        .order_by(Photo.taken_at.desc())
    )
    result = await db.execute(q)
    photos = result.scalars().all()

    groups: dict[str, list] = {}
    for p in photos:
        key = p.taken_at.strftime("%Y-%m") if p.taken_at else "unknown"
        groups.setdefault(key, []).append(_serialize(p))

    return [{"month": k, "photos": v} for k, v in groups.items()]


# ── Map data ──────────────────────────────────────────────────────────────────

@router.get("/map")
async def map_pins(db: AsyncSession = Depends(get_db)):
    q = select(Photo).where(
        Photo.gps_lat.is_not(None),
        Photo.deleted_at.is_(None),
        Photo.is_duplicate == False,  # noqa: E712
    )
    result = await db.execute(q)
    photos = result.scalars().all()
    return [
        {
            "id": p.id,
            "lat": p.gps_lat,
            "lon": p.gps_lon,
            "thumbnail_url": f"/thumbnails/{Path(p.thumbnail_path).name}" if p.thumbnail_path else None,
            "taken_at": p.taken_at.isoformat() if p.taken_at else None,
        }
        for p in photos
    ]


# ── Duplicates ────────────────────────────────────────────────────────────────

@router.get("/duplicates")
async def list_duplicates(db: AsyncSession = Depends(get_db)):
    q = select(Photo).where(Photo.is_duplicate == True, Photo.deleted_at.is_(None))  # noqa: E712
    result = await db.execute(q)
    return {"duplicates": [_serialize(p) for p in result.scalars().all()]}


# ── Trash ─────────────────────────────────────────────────────────────────────

@router.get("/trash")
async def list_trash(db: AsyncSession = Depends(get_db)):
    q = select(Photo).where(Photo.deleted_at.is_not(None)).order_by(Photo.deleted_at.desc())
    result = await db.execute(q)
    return {"photos": [_serialize(p) for p in result.scalars().all()]}


# ── ZIP download ──────────────────────────────────────────────────────────────

class DownloadZipIn(BaseModel):
    photo_ids: list[int]


@router.post("/download-zip")
async def download_zip(body: DownloadZipIn, db: AsyncSession = Depends(get_db)):
    if not body.photo_ids:
        raise HTTPException(status_code=400, detail="No photo IDs provided")
    if len(body.photo_ids) > 500:
        raise HTTPException(status_code=400, detail="Maximum 500 photos per download")

    result = await db.execute(select(Photo).where(Photo.id.in_(body.photo_ids)))
    photos = result.scalars().all()

    def generate():
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in photos:
                fp = Path(p.file_path)
                if fp.exists():
                    zf.write(fp, p.original_filename)
        buf.seek(0)
        yield from iter(lambda: buf.read(65536), b"")

    return StreamingResponse(
        generate(),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=photosync-export.zip"},
    )


# ── Single photo ──────────────────────────────────────────────────────────────

@router.get("/{photo_id}")
async def get_photo(photo_id: int, db: AsyncSession = Depends(get_db)):
    photo = await db.get(Photo, photo_id, options=[selectinload(Photo.tags)])
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    return _serialize(photo)


# ── Soft delete ───────────────────────────────────────────────────────────────

@router.delete("/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_photo(photo_id: int, db: AsyncSession = Depends(get_db)):
    photo = await db.get(Photo, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    photo.deleted_at = datetime.utcnow()
    await db.commit()


# ── Permanent delete ──────────────────────────────────────────────────────────

@router.delete("/{photo_id}/permanent", status_code=status.HTTP_204_NO_CONTENT)
async def permanent_delete(photo_id: int, db: AsyncSession = Depends(get_db)):
    photo = await db.get(Photo, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    for path in (photo.file_path, photo.thumbnail_path):
        if path:
            try:
                os.remove(path)
            except FileNotFoundError:
                pass
    await db.delete(photo)
    await db.commit()


# ── Restore from trash ────────────────────────────────────────────────────────

@router.post("/{photo_id}/restore")
async def restore_photo(photo_id: int, db: AsyncSession = Depends(get_db)):
    photo = await db.get(Photo, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    photo.deleted_at = None
    await db.commit()
    return {"id": photo.id, "restored": True}


# ── Favorite toggle ───────────────────────────────────────────────────────────

@router.post("/{photo_id}/favorite")
async def toggle_favorite(photo_id: int, db: AsyncSession = Depends(get_db)):
    photo = await db.get(Photo, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    photo.is_favorite = not photo.is_favorite
    await db.commit()
    return {"id": photo.id, "is_favorite": photo.is_favorite}


# ── Notes / caption ───────────────────────────────────────────────────────────

class NotesIn(BaseModel):
    notes: str


@router.patch("/{photo_id}/notes")
async def update_notes(photo_id: int, body: NotesIn, db: AsyncSession = Depends(get_db)):
    photo = await db.get(Photo, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    photo.notes = body.notes
    await db.commit()
    return {"id": photo.id, "notes": photo.notes}


# ── Bulk operations ───────────────────────────────────────────────────────────

class BulkIn(BaseModel):
    photo_ids: list[int]


@router.post("/bulk/delete")
async def bulk_delete(body: BulkIn, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        update(Photo)
        .where(Photo.id.in_(body.photo_ids), Photo.deleted_at.is_(None))
        .values(deleted_at=datetime.utcnow())
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
        update(Photo).where(Photo.id.in_(body.photo_ids)).values(deleted_at=None)
    )
    await db.commit()
    return {"restored": result.rowcount}


# ── Mass filter-based cleanup ───────────────────────────────────────────────────

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
    screenshots = await _count_and_size(Photo.is_screenshot == True)  # noqa: E712
    duplicates = await _count_and_size(Photo.is_duplicate == True)  # noqa: E712
    low_quality = await _count_and_size(low_q)
    dark = await _count_and_size(Photo.is_dark == True)  # noqa: E712
    overexposed = await _count_and_size(Photo.is_overexposed == True)  # noqa: E712
    low_res = await _count_and_size(Photo.is_low_res == True)  # noqa: E712
    # Union (a photo may match more than one category — count it once)
    reclaimable = await _count_and_size(
        or_(
            Photo.is_screenshot == True,  # noqa: E712
            Photo.is_duplicate == True,  # noqa: E712
            Photo.is_dark == True,  # noqa: E712
            Photo.is_overexposed == True,  # noqa: E712
            Photo.is_low_res == True,  # noqa: E712
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


# ── Burst groups ────────────────────────────────────────────────────────────────

@router.get("/burst-groups")
async def burst_groups(db: AsyncSession = Depends(get_db)):
    """Photos grouped into bursts, with the sharpest pre-marked as the keeper."""
    photos = (await db.execute(
        select(Photo)
        .where(Photo.burst_id.is_not(None), Photo.deleted_at.is_(None))
        .options(selectinload(Photo.tags))
        .order_by(Photo.burst_id, Photo.taken_at.asc())
    )).scalars().all()

    groups: dict[str, list[Photo]] = {}
    for p in photos:
        groups.setdefault(p.burst_id, []).append(p)

    output = []
    for burst_id, members in groups.items():
        if len(members) < 2:
            continue
        best = max(members, key=lambda p: (p.quality_score or 0))
        output.append({
            "burst_id": burst_id,
            "keep_id": best.id,
            "suggested_delete_ids": [p.id for p in members if p.id != best.id],
            "photos": [_serialize(p) for p in members],
        })
    return {"groups": output, "total_groups": len(output)}


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


@router.post("/empty-trash")
async def empty_trash(
    older_than_days: int | None = Query(None, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Permanently delete trashed photos (optionally only those older than N days).

    Removes files from disk (original, thumbnail, preview) then the rows.
    """
    q = select(Photo).where(Photo.deleted_at.is_not(None))
    if older_than_days is not None:
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=older_than_days)
        q = q.where(Photo.deleted_at <= cutoff)

    photos = (await db.execute(q)).scalars().all()
    removed = 0
    for photo in photos:
        for path in (photo.file_path, photo.thumbnail_path, photo.preview_path):
            if path:
                try:
                    os.remove(path)
                except FileNotFoundError:
                    pass
        await db.delete(photo)
        removed += 1
    await db.commit()
    return {"permanently_deleted": removed}


# ── Library analysis (rescan flags for existing photos) ─────────────────────────

@router.post("/analyze", status_code=status.HTTP_202_ACCEPTED)
async def analyze_library(recompute_quality: bool = Query(True)):
    """Background one-shot analysis: screenshot flags, quality scores, exposure/
    resolution classification, missing previews, near-duplicate clustering, and
    burst grouping. Poll GET /api/jobs/{id}. Run once after a bulk import."""

    async def runner(session: AsyncSession, job) -> dict:
        from services.screenshot_detector import detect_screenshot
        from services.image_processor import recompute_quality as recompute_quality_fn, _classify
        from services.storage import _make_preview
        from services.deduplicator import rescan_duplicates
        from services.bursts import group_bursts
        import uuid

        photos = (await session.execute(
            select(Photo).where(Photo.deleted_at.is_(None))
        )).scalars().all()
        job.total = len(photos)
        await session.commit()

        screenshots_flagged = quality_updated = previews_made = 0
        for idx, photo in enumerate(photos):
            photo.is_screenshot = detect_screenshot(
                width=photo.width, height=photo.height,
                camera_make=photo.camera_make, original_filename=photo.original_filename,
            )
            if photo.is_screenshot:
                screenshots_flagged += 1

            # Backfill a web preview if missing and we still have the original.
            if not photo.preview_path and photo.file_path and Path(photo.file_path).exists():
                pv = await _make_preview(Path(photo.file_path), uuid.uuid4().hex)
                if pv:
                    photo.preview_path = str(pv)
                    previews_made += 1

            src = photo.thumbnail_path or photo.file_path
            if src and Path(src).exists():
                flags = _classify(src, photo.width, photo.height)
                photo.is_dark = flags["is_dark"]
                photo.is_overexposed = flags["is_overexposed"]
                photo.is_low_res = flags["is_low_res"]
                if recompute_quality:
                    score = recompute_quality_fn(src)
                    if score is not None:
                        photo.quality_score = score
                        quality_updated += 1

            if (idx + 1) % 50 == 0 or idx + 1 == len(photos):
                job.processed = idx + 1
                await session.commit()

        dup_summary = await rescan_duplicates(session)
        burst_summary = await group_bursts(session)

        return {
            "scanned": len(photos),
            "screenshots": screenshots_flagged,
            "quality_recomputed": quality_updated,
            "previews_made": previews_made,
            "duplicates": dup_summary,
            "bursts": burst_summary,
        }

    from services.jobs import start_job
    job_id = await start_job("analyze", runner)
    return {"job_id": job_id}


@router.post("/rescan-duplicates", status_code=status.HTTP_202_ACCEPTED)
async def rescan_duplicates_endpoint():
    """Re-cluster near-duplicates across the whole library (background BK-tree)."""
    async def runner(session: AsyncSession, job) -> dict:
        from services.deduplicator import rescan_duplicates
        return await rescan_duplicates(session)

    from services.jobs import start_job
    job_id = await start_job("rescan-duplicates", runner)
    return {"job_id": job_id}


# ── Screenshots ───────────────────────────────────────────────────────────────

@router.get("/screenshots")
async def list_screenshots(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * per_page
    q = (
        select(Photo)
        .where(Photo.is_screenshot == True, Photo.deleted_at.is_(None))  # noqa: E712
        .options(selectinload(Photo.tags))
        .order_by(Photo.created_at.desc())
    )
    total = (await db.execute(q.with_only_columns(func.count()).order_by(None))).scalar_one()
    result = await db.execute(q.offset(offset).limit(per_page))
    return {"total": total, "page": page, "per_page": per_page, "photos": [_serialize(p) for p in result.scalars().all()]}


@router.post("/scan-screenshots")
async def scan_screenshots(db: AsyncSession = Depends(get_db)):
    """Retroactively run screenshot detection on all un-scanned photos."""
    from services.screenshot_detector import detect_screenshot

    result = await db.execute(select(Photo).where(Photo.deleted_at.is_(None)))
    photos = result.scalars().all()
    updated = 0
    for photo in photos:
        detected = detect_screenshot(
            width=photo.width,
            height=photo.height,
            camera_make=photo.camera_make,
            original_filename=photo.original_filename,
        )
        if detected != photo.is_screenshot:
            photo.is_screenshot = detected
            updated += 1
    await db.commit()
    total_screenshots = sum(1 for p in photos if p.is_screenshot)
    return {"scanned": len(photos), "updated": updated, "total_screenshots": total_screenshots}


# ── Duplicate groups ──────────────────────────────────────────────────────────

@router.get("/duplicate-groups")
async def duplicate_groups(db: AsyncSession = Depends(get_db)):
    """Return originals that have at least one duplicate, with duplicates nested."""
    # Find all photos that are originals with at least one duplicate pointing to them
    dup_result = await db.execute(
        select(Photo).where(Photo.is_duplicate == True, Photo.deleted_at.is_(None))  # noqa: E712
        .options(selectinload(Photo.tags))
    )
    duplicates = dup_result.scalars().all()

    # Group by duplicate_of_id
    groups: dict[int, list[Photo]] = {}
    for dup in duplicates:
        if dup.duplicate_of_id:
            groups.setdefault(dup.duplicate_of_id, []).append(dup)

    if not groups:
        return {"groups": []}

    originals_result = await db.execute(
        select(Photo).where(Photo.id.in_(list(groups.keys()))).options(selectinload(Photo.tags))
    )
    originals = {p.id: p for p in originals_result.scalars().all()}

    output = []
    for orig_id, dups in groups.items():
        original = originals.get(orig_id)
        if not original:
            continue
        # Suggest deleting lowest-quality duplicates (keep originals, delete dupes)
        suggested = sorted(dups, key=lambda p: (p.quality_score or 0))
        output.append({
            "original": _serialize(original),
            "duplicates": [_serialize(d) for d in dups],
            "suggested_delete_ids": [d.id for d in suggested],
        })

    return {"groups": output, "total_groups": len(output), "total_duplicates": len(duplicates)}


# ── Triage queue ──────────────────────────────────────────────────────────────

@router.get("/triage-queue")
async def triage_queue(
    include_screenshots: bool = Query(True),
    include_duplicates: bool = Query(True),
    include_low_quality: bool = Query(True),
    quality_threshold: float = Query(0.3, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
):
    """Return an ordered queue of photos that need a keep/delete decision."""
    seen: set[int] = set()
    queue: list[dict] = []

    async def _fetch(condition) -> list[Photo]:
        q = (
            select(Photo)
            .where(condition, Photo.deleted_at.is_(None), Photo.is_favorite == False)  # noqa: E712
            .options(selectinload(Photo.tags))
            .limit(500)
        )
        return (await db.execute(q)).scalars().all()

    if include_screenshots:
        for p in await _fetch(Photo.is_screenshot == True):  # noqa: E712
            if p.id not in seen:
                seen.add(p.id)
                queue.append({**_serialize(p), "triage_reason": "screenshot"})

    if include_duplicates:
        for p in await _fetch(Photo.is_duplicate == True):  # noqa: E712
            if p.id not in seen:
                seen.add(p.id)
                queue.append({**_serialize(p), "triage_reason": "duplicate"})

    if include_low_quality:
        for p in await _fetch(
            (Photo.quality_score <= quality_threshold) & Photo.quality_score.is_not(None)
        ):
            if p.id not in seen:
                seen.add(p.id)
                queue.append({**_serialize(p), "triage_reason": "low_quality"})

    return {"queue": queue, "total": len(queue)}


# ── Serialiser ────────────────────────────────────────────────────────────────

def _serialize(p: Photo) -> dict:
    return {
        "id": p.id,
        "filename": p.original_filename,
        "thumbnail_url": f"/thumbnails/{Path(p.thumbnail_path).name}" if p.thumbnail_path else None,
        "preview_url": f"/previews/{Path(p.preview_path).name}" if p.preview_path else None,
        "original_url": f"/uploads/{p.filename}",
        "width": p.width,
        "height": p.height,
        "taken_at": p.taken_at.isoformat() if p.taken_at else None,
        "camera": f"{p.camera_make or ''} {p.camera_model or ''}".strip() or None,
        "gps": {"lat": p.gps_lat, "lon": p.gps_lon} if p.gps_lat else None,
        "tags": [{"id": t.id, "name": t.name, "source": t.source} for t in (p.tags or [])],
        "ai_tags": json.loads(p.ai_tags) if p.ai_tags else [],
        "is_duplicate": p.is_duplicate,
        "is_screenshot": p.is_screenshot,
        "is_dark": p.is_dark,
        "is_overexposed": p.is_overexposed,
        "is_low_res": p.is_low_res,
        "burst_id": p.burst_id,
        "is_favorite": p.is_favorite,
        "quality_score": p.quality_score,
        "notes": p.notes,
        "file_size": p.file_size,
        "deleted_at": p.deleted_at.isoformat() if p.deleted_at else None,
        "created_at": p.created_at.isoformat(),
    }
