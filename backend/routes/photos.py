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
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from models.photo import Photo
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
        file_path, thumb_path, file_size = await save_upload(file)
        metadata = await process_photo(file_path)

        dup_id = await find_duplicate(db, metadata.get("perceptual_hash"))

        photo = Photo(
            filename=file_path.name,
            original_filename=file.filename or file_path.name,
            file_path=str(file_path),
            thumbnail_path=str(thumb_path) if thumb_path else None,
            file_size=file_size,
            mime_type=file.content_type or "image/jpeg",
            width=metadata.get("width"),
            height=metadata.get("height"),
            taken_at=metadata.get("taken_at"),
            camera_make=metadata.get("camera_make"),
            camera_model=metadata.get("camera_model"),
            gps_lat=metadata.get("gps_lat"),
            gps_lon=metadata.get("gps_lon"),
            perceptual_hash=metadata.get("perceptual_hash"),
            quality_score=metadata.get("quality_score"),
            is_duplicate=dup_id is not None,
            duplicate_of_id=dup_id,
        )
        db.add(photo)
        await db.commit()
        await db.refresh(photo)
        results.append({"id": photo.id, "filename": photo.original_filename, "is_duplicate": photo.is_duplicate})

    return {"uploaded": len(results), "photos": results}


# ── Folder import ─────────────────────────────────────────────────────────────

class FolderImportIn(BaseModel):
    path: str
    recursive: bool = True


@router.post("/import-folder")
async def import_folder(body: FolderImportIn, db: AsyncSession = Depends(get_db)):
    folder = Path(body.path)
    if not folder.exists() or not folder.is_dir():
        raise HTTPException(status_code=400, detail="Path does not exist or is not a directory")

    pattern = "**/*" if body.recursive else "*"
    files = [p for p in folder.glob(pattern) if p.is_file() and is_image(p.name)]

    imported, skipped, duplicates = 0, 0, 0
    for file_path in files:
        # Skip already-imported paths
        existing = await db.execute(select(Photo).where(Photo.file_path == str(file_path)))
        if existing.scalar_one_or_none():
            skipped += 1
            continue

        metadata = await process_photo(file_path)
        dup_id = await find_duplicate(db, metadata.get("perceptual_hash"))

        # Generate thumbnail for imported file
        from services.storage import _make_thumbnail
        import uuid
        stem = uuid.uuid4().hex
        thumb_path = await _make_thumbnail(file_path, stem)

        photo = Photo(
            filename=file_path.name,
            original_filename=file_path.name,
            file_path=str(file_path),
            thumbnail_path=str(thumb_path) if thumb_path else None,
            file_size=file_path.stat().st_size,
            mime_type="image/jpeg",
            width=metadata.get("width"),
            height=metadata.get("height"),
            taken_at=metadata.get("taken_at"),
            camera_make=metadata.get("camera_make"),
            camera_model=metadata.get("camera_model"),
            gps_lat=metadata.get("gps_lat"),
            gps_lon=metadata.get("gps_lon"),
            perceptual_hash=metadata.get("perceptual_hash"),
            quality_score=metadata.get("quality_score"),
            is_duplicate=dup_id is not None,
            duplicate_of_id=dup_id,
        )
        db.add(photo)
        await db.commit()
        imported += 1
        if dup_id:
            duplicates += 1

    return {"imported": imported, "skipped": skipped, "duplicates_found": duplicates}


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
    result = await db.execute(select(Photo).where(Photo.id.in_(body.photo_ids)))
    now = datetime.utcnow()
    count = 0
    for photo in result.scalars().all():
        photo.deleted_at = now
        count += 1
    await db.commit()
    return {"deleted": count}


@router.post("/bulk/favorite")
async def bulk_favorite(body: BulkIn, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Photo).where(Photo.id.in_(body.photo_ids)))
    count = 0
    for photo in result.scalars().all():
        photo.is_favorite = True
        count += 1
    await db.commit()
    return {"favorited": count}


@router.post("/bulk/restore")
async def bulk_restore(body: BulkIn, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Photo).where(Photo.id.in_(body.photo_ids)))
    count = 0
    for photo in result.scalars().all():
        photo.deleted_at = None
        count += 1
    await db.commit()
    return {"restored": count}


# ── Serialiser ────────────────────────────────────────────────────────────────

def _serialize(p: Photo) -> dict:
    return {
        "id": p.id,
        "filename": p.original_filename,
        "thumbnail_url": f"/thumbnails/{Path(p.thumbnail_path).name}" if p.thumbnail_path else None,
        "original_url": f"/uploads/{p.filename}",
        "width": p.width,
        "height": p.height,
        "taken_at": p.taken_at.isoformat() if p.taken_at else None,
        "camera": f"{p.camera_make or ''} {p.camera_model or ''}".strip() or None,
        "gps": {"lat": p.gps_lat, "lon": p.gps_lon} if p.gps_lat else None,
        "tags": [{"id": t.id, "name": t.name, "source": t.source} for t in (p.tags or [])],
        "ai_tags": json.loads(p.ai_tags) if p.ai_tags else [],
        "is_duplicate": p.is_duplicate,
        "is_favorite": p.is_favorite,
        "quality_score": p.quality_score,
        "notes": p.notes,
        "file_size": p.file_size,
        "deleted_at": p.deleted_at.isoformat() if p.deleted_at else None,
        "created_at": p.created_at.isoformat(),
    }
