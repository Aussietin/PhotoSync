"""
Export: get cleaned results out of PhotoSync.

A web app can't delete from the iOS camera roll, so the deliverables are:
  - a streaming ZIP of the *keepers* (write to a temp file on disk, not memory),
  - a *deletion plan* (CSV/JSON) listing what's in Trash so you can act on the
    phone or feed it to an iOS Shortcut.
"""
import csv
import io
import os
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.background import BackgroundTask

from database import get_db
from models.photo import Photo

router = APIRouter()


def _reason_for(p: Photo) -> str:
    reasons = []
    if p.is_screenshot:
        reasons.append("screenshot")
    if p.is_duplicate:
        reasons.append("duplicate")
    if p.is_low_res:
        reasons.append("low-res")
    if p.is_dark:
        reasons.append("dark")
    if p.is_overexposed:
        reasons.append("overexposed")
    return ",".join(reasons) or "manual"


@router.get("/keepers")
async def export_keepers(
    exclude_screenshots: bool = Query(True),
    exclude_low_quality: bool = Query(False),
    min_quality: float = Query(0.0, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
):
    """Stream a ZIP of the keepers — live, non-duplicate photos. Built on disk so
    a 20k-photo export doesn't blow up memory."""
    q = select(Photo).where(Photo.deleted_at.is_(None), Photo.is_duplicate == False)  # noqa: E712
    if exclude_screenshots:
        q = q.where(Photo.is_screenshot == False)  # noqa: E712
    if exclude_low_quality:
        q = q.where((Photo.quality_score.is_(None)) | (Photo.quality_score > min_quality))

    photos = (await db.execute(q)).scalars().all()
    if not photos:
        raise HTTPException(status_code=404, detail="No photos match the keeper filters")

    tmp = tempfile.NamedTemporaryFile(prefix="photosync-keepers-", suffix=".zip", delete=False)
    tmp.close()
    with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as zf:
        seen: set[str] = set()
        for p in photos:
            src = Path(p.file_path)
            if not src.exists():
                continue
            # Organise by year/month of capture for a tidy archive.
            when = p.taken_at or p.created_at
            folder = when.strftime("%Y/%m") if when else "undated"
            arc = f"{folder}/{p.original_filename}"
            if arc in seen:  # avoid clobbering duplicate filenames
                arc = f"{folder}/{p.id}_{p.original_filename}"
            seen.add(arc)
            zf.write(src, arc)

    return FileResponse(
        tmp.name,
        media_type="application/zip",
        filename=f"photosync-keepers-{datetime.now():%Y%m%d}.zip",
        background=BackgroundTask(os.remove, tmp.name),
    )


@router.get("/deletion-plan")
async def deletion_plan(
    fmt: str = Query("csv", pattern="^(csv|json)$"),
    db: AsyncSession = Depends(get_db),
):
    """List everything currently in Trash so it can be deleted on the device."""
    photos = (await db.execute(
        select(Photo).where(Photo.deleted_at.is_not(None)).order_by(Photo.taken_at.asc())
    )).scalars().all()

    rows = [{
        "filename": p.original_filename,
        "reason": _reason_for(p),
        "taken_at": p.taken_at.isoformat() if p.taken_at else "",
        "width": p.width or "",
        "height": p.height or "",
        "file_size_bytes": p.file_size,
    } for p in photos]

    if fmt == "json":
        return {"count": len(rows), "photos": rows}

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["filename", "reason", "taken_at", "width", "height", "file_size_bytes"])
    writer.writeheader()
    writer.writerows(rows)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=photosync-deletion-plan.csv"},
    )
