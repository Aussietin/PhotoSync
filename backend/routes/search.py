from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from models.photo import Photo, Tag
from routes.photos import _serialize
from services import embeddings

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


@router.get("/semantic")
async def semantic_search(
    q: str = Query(..., min_length=1, description="Natural-language query, e.g. 'dog at the beach'"),
    limit: int = Query(50, ge=1, le=200),
    min_score: float = Query(0.18, ge=0.0, le=1.0, description="Minimum cosine similarity"),
    db: AsyncSession = Depends(get_db),
):
    """Semantic (meaning-based) search using local CLIP embeddings.

    Embeds the query text on-device and ranks photos by cosine similarity to
    their stored image embeddings. Nothing leaves the machine. Requires the
    optional CLIP model and an analyze pass to have populated embeddings.
    """
    query_vec = embeddings.embed_text(q)
    if query_vec is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Local AI model not installed. Run "
                "`pip install -r requirements-ai.txt`, then POST /api/photos/analyze "
                "to index your library for semantic search."
            ),
        )

    # Pull candidate photos that have an embedding. At 20k this is a small,
    # fast scan; the similarity maths below is a single numpy matrix product.
    rows = (await db.execute(
        select(Photo)
        .where(
            Photo.clip_embedding.is_not(None),
            Photo.deleted_at.is_(None),
            Photo.is_duplicate == False,  # noqa: E712
        )
        .options(selectinload(Photo.tags))
    )).scalars().all()

    if not rows:
        return {
            "count": 0,
            "query": q,
            "photos": [],
            "hint": "No indexed photos yet — run POST /api/photos/analyze first.",
        }

    scores = embeddings.rank_by_similarity(query_vec, [p.clip_embedding for p in rows])
    ranked = sorted(zip(rows, scores), key=lambda pair: pair[1], reverse=True)

    photos = []
    for photo, score in ranked:
        if score < min_score:
            break
        photos.append({**_serialize(photo), "score": round(float(score), 4)})
        if len(photos) >= limit:
            break

    return {"count": len(photos), "query": q, "photos": photos}
