"""Read-only views over the library: lists, timeline, map, groupings, ZIP."""
import asyncio
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
from routes.photos.cleanup import _large_condition
from routes.photos.serialize import _serialize

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
    # selectinload(tags) is required: _serialize reads p.tags, and async lazy-load
    # raises MissingGreenlet (same fix as /trash).
    q = (
        select(Photo)
        .where(Photo.is_duplicate == True, Photo.deleted_at.is_(None))  # noqa: E712
        .options(selectinload(Photo.tags))
    )
    result = await db.execute(q)
    return {"duplicates": [_serialize(p) for p in result.scalars().all()]}


# ── Trash ─────────────────────────────────────────────────────────────────────

@router.get("/trash")
async def list_trash(db: AsyncSession = Depends(get_db)):
    q = (
        select(Photo)
        .where(Photo.deleted_at.is_not(None))
        .options(selectinload(Photo.tags))
        .order_by(Photo.deleted_at.desc())
    )
    result = await db.execute(q)
    return {"photos": [_serialize(p) for p in result.scalars().all()]}


def _write_zip(dest: str, entries: list[tuple[str, str, int]]) -> None:
    """Write (file_path, archive_name, photo_id) entries into a ZIP at dest,
    skipping files that have gone missing and de-duplicating archive names."""
    seen: set[str] = set()
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path, name, photo_id in entries:
            fp = Path(file_path)
            if not fp.exists():
                continue
            arc = name if name not in seen else f"{photo_id}_{name}"
            seen.add(arc)
            zf.write(fp, arc)


# ── ZIP download ──────────────────────────────────────────────────────────────

class DownloadZipIn(BaseModel):
    photo_ids: list[int]


@router.post("/download-zip")
async def download_zip(body: DownloadZipIn, db: AsyncSession = Depends(get_db)):
    """Build a ZIP of the requested photos on disk and return it as a download.

    Writes to a temp file (not memory) so arbitrarily large selections work.
    No photo-count cap — the server-side streaming keepers export is the recommended
    path for 20k+ photos, but this handles any manual selection cleanly.
    """
    if not body.photo_ids:
        raise HTTPException(status_code=400, detail="No photo IDs provided")

    result = await db.execute(select(Photo).where(Photo.id.in_(body.photo_ids)))
    photos = result.scalars().all()
    if not photos:
        raise HTTPException(status_code=404, detail="No matching photos found")

    tmp = tempfile.NamedTemporaryFile(prefix="photosync-download-", suffix=".zip", delete=False)
    tmp.close()
    entries = [(p.file_path, p.original_filename, p.id) for p in photos]
    # Compressing a few thousand photos takes minutes; doing it inline froze
    # the whole server for that long.
    await asyncio.to_thread(_write_zip, tmp.name, entries)

    return FileResponse(
        tmp.name,
        media_type="application/zip",
        filename=f"photosync-export-{datetime.now():%Y%m%d}.zip",
        background=BackgroundTask(os.remove, tmp.name),
    )


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


# ── Large files (mostly videos) ─────────────────────────────────────────────────

@router.get("/large")
async def list_large(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Biggest files first — the space hogs (videos, ProRAW, panoramas)."""
    offset = (page - 1) * per_page
    q = (
        select(Photo)
        .where(_large_condition(), Photo.deleted_at.is_(None))
        .options(selectinload(Photo.tags))
        .order_by(Photo.file_size.desc())
    )
    total = (await db.execute(q.with_only_columns(func.count()).order_by(None))).scalar_one()
    total_bytes = (await db.execute(
        select(func.coalesce(func.sum(Photo.file_size), 0))
        .where(_large_condition(), Photo.deleted_at.is_(None))
    )).scalar_one()
    result = await db.execute(q.offset(offset).limit(per_page))
    return {
        "total": total,
        "total_bytes": int(total_bytes),
        "threshold_mb": settings.LARGE_FILE_MB,
        "page": page,
        "per_page": per_page,
        "photos": [_serialize(p) for p in result.scalars().all()],
    }


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
