import json
from typing import Optional
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.photo import Photo
from services.storage import save_upload
from services.image_processor import process_photo
from services.deduplicator import find_duplicate

router = APIRouter()


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
            is_duplicate=dup_id is not None,
            duplicate_of_id=dup_id,
        )
        db.add(photo)
        await db.commit()
        await db.refresh(photo)
        results.append({"id": photo.id, "filename": photo.original_filename, "is_duplicate": photo.is_duplicate})

    return {"uploaded": len(results), "photos": results}


@router.get("")
async def list_photos(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    include_duplicates: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * per_page
    q = select(Photo)
    if not include_duplicates:
        q = q.where(Photo.is_duplicate == False)  # noqa: E712
    q = q.order_by(Photo.taken_at.desc().nullslast()).offset(offset).limit(per_page)

    result = await db.execute(q)
    photos = result.scalars().all()

    count_q = select(func.count()).select_from(Photo)
    if not include_duplicates:
        count_q = count_q.where(Photo.is_duplicate == False)  # noqa: E712
    total = (await db.execute(count_q)).scalar_one()

    return {"total": total, "page": page, "per_page": per_page, "photos": [_serialize(p) for p in photos]}


@router.get("/timeline")
async def timeline(db: AsyncSession = Depends(get_db)):
    q = select(Photo).where(Photo.taken_at.is_not(None), Photo.is_duplicate == False).order_by(Photo.taken_at.desc())  # noqa: E712
    result = await db.execute(q)
    photos = result.scalars().all()

    groups: dict[str, list] = {}
    for p in photos:
        key = p.taken_at.strftime("%Y-%m") if p.taken_at else "unknown"
        groups.setdefault(key, []).append(_serialize(p))

    return [{"month": k, "photos": v} for k, v in groups.items()]


@router.get("/duplicates")
async def list_duplicates(db: AsyncSession = Depends(get_db)):
    q = select(Photo).where(Photo.is_duplicate == True)  # noqa: E712
    result = await db.execute(q)
    return {"duplicates": [_serialize(p) for p in result.scalars().all()]}


@router.get("/{photo_id}")
async def get_photo(photo_id: int, db: AsyncSession = Depends(get_db)):
    photo = await db.get(Photo, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    return _serialize(photo)


@router.delete("/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_photo(photo_id: int, db: AsyncSession = Depends(get_db)):
    photo = await db.get(Photo, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    await db.delete(photo)
    await db.commit()


def _serialize(p: Photo) -> dict:
    return {
        "id": p.id,
        "filename": p.original_filename,
        "thumbnail_url": f"/thumbnails/{p.thumbnail_path.split('/')[-1]}" if p.thumbnail_path else None,
        "original_url": f"/uploads/{p.filename}",
        "width": p.width,
        "height": p.height,
        "taken_at": p.taken_at.isoformat() if p.taken_at else None,
        "camera": f"{p.camera_make or ''} {p.camera_model or ''}".strip() or None,
        "gps": {"lat": p.gps_lat, "lon": p.gps_lon} if p.gps_lat else None,
        "tags": [{"id": t.id, "name": t.name, "source": t.source} for t in p.tags],
        "ai_tags": json.loads(p.ai_tags) if p.ai_tags else [],
        "is_duplicate": p.is_duplicate,
        "file_size": p.file_size,
        "created_at": p.created_at.isoformat(),
    }
