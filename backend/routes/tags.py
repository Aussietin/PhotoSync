from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.photo import Photo, Tag

router = APIRouter()


class TagIn(BaseModel):
    name: str


@router.get("")
async def list_tags(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Tag.name).distinct())
    return {"tags": sorted(r[0] for r in result.all())}


@router.post("/{photo_id}")
async def add_tag(photo_id: int, body: TagIn, db: AsyncSession = Depends(get_db)):
    photo = await db.get(Photo, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    tag = Tag(photo_id=photo_id, name=body.name.lower().strip(), source="manual")
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return {"id": tag.id, "name": tag.name, "photo_id": photo_id}


@router.delete("/{tag_id}")
async def delete_tag(tag_id: int, db: AsyncSession = Depends(get_db)):
    tag = await db.get(Tag, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    await db.delete(tag)
    await db.commit()
    return {"deleted": tag_id}
