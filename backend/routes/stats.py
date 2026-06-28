from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends

from database import get_db
from models.photo import Photo, Tag

router = APIRouter()


@router.get("")
async def get_stats(db: AsyncSession = Depends(get_db)):
    base = select(Photo).where(Photo.deleted_at.is_(None), Photo.is_duplicate == False)  # noqa: E712

    total = (await db.execute(base.with_only_columns(func.count()).order_by(None))).scalar_one()
    total_size = (await db.execute(
        base.with_only_columns(func.coalesce(func.sum(Photo.file_size), 0)).order_by(None)
    )).scalar_one()
    favorites = (await db.execute(
        base.where(Photo.is_favorite == True).with_only_columns(func.count()).order_by(None)  # noqa: E712
    )).scalar_one()
    duplicates = (await db.execute(
        select(func.count()).select_from(Photo).where(Photo.is_duplicate == True, Photo.deleted_at.is_(None))  # noqa: E712
    )).scalar_one()
    with_gps = (await db.execute(
        base.where(Photo.gps_lat.is_not(None)).with_only_columns(func.count()).order_by(None)
    )).scalar_one()
    in_trash = (await db.execute(
        select(func.count()).select_from(Photo).where(Photo.deleted_at.is_not(None))
    )).scalar_one()

    # Monthly breakdown (last 24 months)
    monthly_rows = (await db.execute(
        select(
            func.strftime("%Y-%m", Photo.taken_at).label("month"),
            func.count().label("count"),
        )
        .where(Photo.deleted_at.is_(None), Photo.taken_at.is_not(None), Photo.is_duplicate == False)  # noqa: E712
        .group_by(text("month"))
        .order_by(text("month desc"))
        .limit(24)
    )).all()

    # Top tags
    tag_rows = (await db.execute(
        select(Tag.name, func.count().label("count"))
        .group_by(Tag.name)
        .order_by(func.count().desc())
        .limit(15)
    )).all()

    # Camera breakdown
    camera_rows = (await db.execute(
        select(
            func.coalesce(Photo.camera_model, "Unknown").label("camera"),
            func.count().label("count"),
        )
        .where(Photo.deleted_at.is_(None), Photo.is_duplicate == False)  # noqa: E712
        .group_by(text("camera"))
        .order_by(func.count().desc())
        .limit(10)
    )).all()

    # Avg quality
    avg_quality = (await db.execute(
        base.with_only_columns(func.avg(Photo.quality_score)).order_by(None)
    )).scalar_one()

    return {
        "total_photos": total,
        "total_size_bytes": total_size,
        "favorites": favorites,
        "duplicates": duplicates,
        "with_gps": with_gps,
        "in_trash": in_trash,
        "avg_quality": round(float(avg_quality), 3) if avg_quality else None,
        "photos_by_month": [{"month": r.month, "count": r.count} for r in monthly_rows],
        "top_tags": [{"name": r.name, "count": r.count} for r in tag_rows],
        "cameras": [{"camera": r.camera, "count": r.count} for r in camera_rows],
    }
