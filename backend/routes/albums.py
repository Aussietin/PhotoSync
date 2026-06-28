from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from models.photo import Album, Photo, photo_albums
from routes.photos import _serialize

router = APIRouter()


class AlbumIn(BaseModel):
    name: str
    description: str | None = None


class AlbumPhotosIn(BaseModel):
    photo_ids: list[int]


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.get("")
async def list_albums(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Album).options(selectinload(Album.photos)).order_by(Album.created_at.desc())
    )
    albums = result.scalars().all()
    return {"albums": [_serialize_album(a) for a in albums]}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_album(body: AlbumIn, db: AsyncSession = Depends(get_db)):
    album = Album(name=body.name, description=body.description)
    db.add(album)
    await db.commit()
    await db.refresh(album)
    return _serialize_album(album)


@router.get("/{album_id}")
async def get_album(album_id: int, db: AsyncSession = Depends(get_db)):
    album = await db.get(Album, album_id, options=[selectinload(Album.photos).selectinload(Photo.tags)])
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    return {**_serialize_album(album), "photos": [_serialize(p) for p in album.photos if not p.deleted_at]}


@router.patch("/{album_id}")
async def update_album(album_id: int, body: AlbumIn, db: AsyncSession = Depends(get_db)):
    album = await db.get(Album, album_id)
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    album.name = body.name
    if body.description is not None:
        album.description = body.description
    await db.commit()
    return _serialize_album(album)


@router.delete("/{album_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_album(album_id: int, db: AsyncSession = Depends(get_db)):
    album = await db.get(Album, album_id)
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    await db.delete(album)
    await db.commit()


# ── Photo membership ──────────────────────────────────────────────────────────

@router.post("/{album_id}/photos")
async def add_photos(album_id: int, body: AlbumPhotosIn, db: AsyncSession = Depends(get_db)):
    album = await db.get(Album, album_id, options=[selectinload(Album.photos)])
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")

    result = await db.execute(select(Photo).where(Photo.id.in_(body.photo_ids)))
    photos = result.scalars().all()

    existing_ids = {p.id for p in album.photos}
    for photo in photos:
        if photo.id not in existing_ids:
            album.photos.append(photo)

    # Auto-set cover if none
    if not album.cover_photo_id and photos:
        album.cover_photo_id = photos[0].id

    await db.commit()
    return {"added": len(photos)}


@router.delete("/{album_id}/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_photo(album_id: int, photo_id: int, db: AsyncSession = Depends(get_db)):
    album = await db.get(Album, album_id, options=[selectinload(Album.photos)])
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    album.photos = [p for p in album.photos if p.id != photo_id]
    if album.cover_photo_id == photo_id:
        album.cover_photo_id = album.photos[0].id if album.photos else None
    await db.commit()


@router.patch("/{album_id}/cover/{photo_id}")
async def set_cover(album_id: int, photo_id: int, db: AsyncSession = Depends(get_db)):
    album = await db.get(Album, album_id)
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    album.cover_photo_id = photo_id
    await db.commit()
    return {"cover_photo_id": photo_id}


# ── Serialiser ────────────────────────────────────────────────────────────────

def _serialize_album(a: Album) -> dict:
    photos = [p for p in (a.photos or []) if not p.deleted_at]
    cover = None
    if a.cover_photo_id:
        for p in photos:
            if p.id == a.cover_photo_id and p.thumbnail_path:
                from pathlib import Path
                cover = f"/thumbnails/{Path(p.thumbnail_path).name}"
                break
    if not cover and photos:
        p = photos[0]
        if p.thumbnail_path:
            from pathlib import Path
            cover = f"/thumbnails/{Path(p.thumbnail_path).name}"

    return {
        "id": a.id,
        "name": a.name,
        "description": a.description,
        "photo_count": len(photos),
        "cover_url": cover,
        "created_at": a.created_at.isoformat(),
    }
