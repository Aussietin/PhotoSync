"""
Face indexing + incremental clustering.

``index_photo_faces`` detects and stores the faces in one photo (off the event
loop). ``assign_unclustered`` groups any not-yet-assigned faces into Person
clusters using a running-centroid nearest-match — incremental, so re-running an
analyze only folds in *new* faces and never disturbs people the user has already
named. Pure on-device; no network, no external API.
"""
import asyncio
import uuid
from pathlib import Path

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.photo import Face, Person, Photo
from services import faces


async def index_photo_faces(session: AsyncSession, photo: Photo) -> int:
    """Detect faces for one photo and persist them (person_id left NULL).

    Returns the number of faces stored. No-op if the model is unavailable or the
    original file is missing. CPU-bound detection runs in a thread so the server
    stays responsive during a big analyze pass.
    """
    src = photo.file_path
    if not src or not Path(src).exists():
        return 0

    detections = await asyncio.to_thread(faces.detect_faces, Path(src))
    stored = 0
    for det in detections:
        stem = uuid.uuid4().hex
        crop = await asyncio.to_thread(
            faces.save_face_crop, Path(src), det["bbox"], Path(settings.FACE_DIR) / f"{stem}.jpg"
        )
        x, y, w, h = det["bbox"]
        session.add(Face(
            photo_id=photo.id,
            embedding=faces.to_blob(det["embedding"]),
            bbox_x=x, bbox_y=y, bbox_w=w, bbox_h=h,
            det_score=det["det_score"],
            crop_path=str(crop) if crop else None,
        ))
        stored += 1
    return stored


async def assign_unclustered(session: AsyncSession) -> dict:
    """Cluster every face with no person yet into Person groups (incremental)."""
    # Seed centroids from existing persons so previously-named people are preserved.
    persons = (await session.execute(select(Person))).scalars().all()
    centroids: list[tuple[int, "object"]] = [
        (p.id, faces.from_blob(p.centroid)) for p in persons if p.centroid
    ]
    counts = {p.id: p.face_count for p in persons}
    cover = {p.id: p.cover_face_id for p in persons}

    unassigned = (await session.execute(
        select(Face).where(Face.person_id.is_(None)).order_by(Face.det_score.desc().nullslast())
    )).scalars().all()

    new_people = 0
    for face in unassigned:
        vec = faces.from_blob(face.embedding)
        pid = faces.best_match(vec, centroids)
        if pid is None:
            person = Person(centroid=faces.to_blob(vec), face_count=1, cover_face_id=face.id)
            session.add(person)
            await session.flush()  # get person.id
            pid = person.id
            centroids.append((pid, vec))
            counts[pid] = 1
            cover[pid] = face.id
            new_people += 1
        else:
            n = counts.get(pid, 0)
            new_c = faces.updated_centroid(
                dict(centroids)[pid], n, vec
            )
            counts[pid] = n + 1
            centroids = [(i, new_c if i == pid else c) for i, c in centroids]
        face.person_id = pid

    # Persist updated centroids / counts / covers back onto Person rows.
    for p in (await session.execute(select(Person))).scalars().all():
        if p.id in counts:
            p.face_count = counts[p.id]
            if p.id in dict(centroids):
                p.centroid = faces.to_blob(dict(centroids)[p.id])
            if not p.cover_face_id and cover.get(p.id):
                p.cover_face_id = cover[p.id]

    await session.commit()
    total_people = (await session.execute(select(func.count()).select_from(Person))).scalar_one()
    return {"new_people": new_people, "clustered": len(unassigned), "total_people": total_people}
