"""
People — face clusters discovered by local face recognition.

Browse the auto-discovered people, name the ones you recognise, and bulk-trash
the photos of anyone you don't. Everything here is derived from on-device face
embeddings; no image or identity ever leaves the machine.
"""
import uuid
from datetime import datetime
from pathlib import Path

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, update, distinct
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from models.photo import Photo, Face, Person, DeletionLog
from routes.photos import _serialize, _tok
from services import faces as faces_svc

router = APIRouter()


def _crop_url(crop_path: str | None) -> str | None:
    return f"/faces/{Path(crop_path).name}{_tok()}" if crop_path else None


async def _live_photo_counts(db: AsyncSession) -> dict[int, int]:
    """person_id -> number of distinct live (non-trashed) photos they appear in."""
    rows = (await db.execute(
        select(Face.person_id, func.count(distinct(Face.photo_id)))
        .join(Photo, Photo.id == Face.photo_id)
        .where(Face.person_id.is_not(None), Photo.deleted_at.is_(None))
        .group_by(Face.person_id)
    )).all()
    return {pid: n for pid, n in rows}


@router.get("")
async def list_people(
    min_photos: int = Query(1, ge=1, description="Hide clusters with fewer live photos"),
    known: bool | None = Query(None, description="Filter by named/known status"),
    db: AsyncSession = Depends(get_db),
):
    """All discovered people, most-photographed first. Name the ones you know."""
    counts = await _live_photo_counts(db)
    persons = (await db.execute(select(Person))).scalars().all()

    # Cover-face crop paths in one lookup.
    cover_ids = [p.cover_face_id for p in persons if p.cover_face_id]
    crops: dict[int, str] = {}
    if cover_ids:
        crops = {f.id: f.crop_path for f in (await db.execute(
            select(Face).where(Face.id.in_(cover_ids))
        )).scalars().all()}

    out = []
    for p in persons:
        n = counts.get(p.id, 0)
        if n < min_photos:
            continue
        if known is not None and bool(p.is_known) != known:
            continue
        out.append({
            "id": p.id,
            "name": p.name,
            "is_known": p.is_known,
            "photo_count": n,
            "cover_url": _crop_url(crops.get(p.cover_face_id)),
        })
    out.sort(key=lambda d: d["photo_count"], reverse=True)
    return {"people": out, "total": len(out)}


class PersonUpdate(BaseModel):
    name: str | None = None
    is_known: bool | None = None


@router.patch("/{person_id}")
async def update_person(person_id: int, body: PersonUpdate, db: AsyncSession = Depends(get_db)):
    """Name a person and/or mark them known. Naming implies known unless told otherwise."""
    person = await db.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    if body.name is not None:
        person.name = body.name.strip() or None
        if body.is_known is None and person.name:
            person.is_known = True
    if body.is_known is not None:
        person.is_known = body.is_known
    await db.commit()
    return {"id": person.id, "name": person.name, "is_known": person.is_known}


@router.get("/{person_id}/photos")
async def person_photos(
    person_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Live photos this person appears in (most recent first)."""
    if not await db.get(Person, person_id):
        raise HTTPException(status_code=404, detail="Person not found")
    base = (
        select(Photo)
        .join(Face, Face.photo_id == Photo.id)
        .where(Face.person_id == person_id, Photo.deleted_at.is_(None))
        .distinct()
    )
    total = (await db.execute(
        select(func.count(distinct(Photo.id)))
        .select_from(Photo).join(Face, Face.photo_id == Photo.id)
        .where(Face.person_id == person_id, Photo.deleted_at.is_(None))
    )).scalar_one()
    offset = (page - 1) * per_page
    rows = (await db.execute(
        base.options(selectinload(Photo.tags))
        .order_by(Photo.taken_at.desc().nullslast())
        .offset(offset).limit(per_page)
    )).scalars().all()
    return {"total": total, "page": page, "per_page": per_page,
            "photos": [_serialize(p) for p in rows]}


@router.post("/{person_id}/trash-photos")
async def trash_person_photos(person_id: int, db: AsyncSession = Depends(get_db)):
    """Send every (non-favorite) live photo of this person to Trash, undoably."""
    person = await db.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    photo_ids = (await db.execute(
        select(distinct(Face.photo_id))
        .join(Photo, Photo.id == Face.photo_id)
        .where(Face.person_id == person_id, Photo.deleted_at.is_(None),
               Photo.is_favorite == False)  # noqa: E712
    )).scalars().all()
    if not photo_ids:
        return {"deleted": 0, "batch": None}

    batch = uuid.uuid4().hex
    result = await db.execute(
        update(Photo).where(Photo.id.in_(photo_ids))
        .values(deleted_at=datetime.utcnow(), deleted_batch=batch)
    )
    db.add(DeletionLog(batch=batch, reason=f"person:{person.name or person_id}", count=result.rowcount))
    await db.commit()
    return {"deleted": result.rowcount, "batch": batch}


class MergeIn(BaseModel):
    other_id: int  # this person is merged INTO {person_id}


@router.post("/{person_id}/merge")
async def merge_people(person_id: int, body: MergeIn, db: AsyncSession = Depends(get_db)):
    """Merge ``other_id`` into ``person_id`` (face clustering sometimes over-splits)."""
    target = await db.get(Person, person_id)
    other = await db.get(Person, body.other_id)
    if not target or not other or target.id == other.id:
        raise HTTPException(status_code=400, detail="Invalid merge")
    await db.execute(
        update(Face).where(Face.person_id == other.id).values(person_id=target.id)
    )
    if not target.is_known and other.is_known:
        target.is_known, target.name = other.is_known, target.name or other.name
    await db.delete(other)

    # Recompute the centroid + count from the merged face set so future faces
    # still match this person.
    embs = (await db.execute(
        select(Face.embedding).where(Face.person_id == target.id)
    )).scalars().all()
    if embs:
        mean = np.vstack([faces_svc.from_blob(b) for b in embs]).mean(axis=0)
        norm = float(np.linalg.norm(mean))
        target.centroid = faces_svc.to_blob(mean / norm if norm else mean)
        target.face_count = len(embs)
    await db.commit()
    return {"id": target.id, "merged": other.id}
