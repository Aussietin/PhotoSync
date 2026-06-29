from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from models.photo import Photo, Tag
from routes.photos import _serialize

router = APIRouter()


@router.get("")
async def search_photos(
    q: Optional[str] = Query(None, description="Free-text search across tags and filenames"),
    tag: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    camera: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Photo).where(Photo.is_duplicate == False)  # noqa: E712

    if q:
        term = f"%{q.lower()}%"
        tag_subq = select(Tag.photo_id).where(Tag.name.ilike(term))
        stmt = stmt.where(
            or_(
                Photo.original_filename.ilike(term),
                Photo.id.in_(tag_subq),
                # ai_description is a plain text column; ai_tags is stored as a
                # JSON array string so LIKE catches individual tag words too.
                Photo.ai_description.ilike(term),
                Photo.ai_tags.ilike(term),
            )
        )

    if tag:
        tag_subq = select(Tag.photo_id).where(Tag.name == tag.lower().strip())
        stmt = stmt.where(Photo.id.in_(tag_subq))

    if date_from:
        stmt = stmt.where(Photo.taken_at >= date_from)

    if date_to:
        stmt = stmt.where(Photo.taken_at <= date_to)

    if camera:
        term = f"%{camera}%"
        stmt = stmt.where(or_(Photo.camera_make.ilike(term), Photo.camera_model.ilike(term)))

    offset = (page - 1) * per_page
    stmt = (
        stmt.options(selectinload(Photo.tags))
        .order_by(Photo.taken_at.desc().nullslast())
        .offset(offset)
        .limit(per_page)
    )

    result = await db.execute(stmt)
    photos = result.scalars().all()
    return {"count": len(photos), "page": page, "photos": [_serialize(p) for p in photos]}
