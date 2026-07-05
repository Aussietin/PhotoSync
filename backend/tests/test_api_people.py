"""
Face clustering + People API.

Uses synthetic, hand-built face embeddings so the clustering logic is tested
deterministically without loading the InsightFace model. Two near-identical
vectors must land in one person; an orthogonal vector must form a second.
"""
from datetime import datetime

import numpy as np

from models.photo import Photo, Face, Person, DeletionLog
from services import faces as faces_svc
from services import face_clustering


def _unit(v) -> np.ndarray:
    v = np.asarray(v, dtype=np.float32)
    return v / np.linalg.norm(v)


def _vec(axis: int, jitter: float = 0.0) -> np.ndarray:
    v = np.zeros(512, dtype=np.float32)
    v[axis] = 1.0
    if jitter:
        v[axis + 1] = jitter
    return _unit(v)


def _photo(**kw) -> Photo:
    d = dict(filename="x.jpg", original_filename="x.jpg",
             file_path=f"/fake/{abs(hash(str(kw)))}.jpg", file_size=1024,
             mime_type="image/jpeg", created_at=datetime.utcnow(), updated_at=datetime.utcnow())
    d.update(kw)
    return Photo(**d)


async def _seed(session, objs):
    for o in objs:
        session.add(o)
    await session.commit()
    for o in objs:
        await session.refresh(o)
    return objs


async def test_cluster_and_people_api(client, db_session):
    pa, pb, pc = await _seed(db_session, [
        _photo(file_path="/fake/a.jpg"),
        _photo(file_path="/fake/b.jpg"),
        _photo(file_path="/fake/c.jpg"),
    ])
    # Person 1 appears in A and B (near-identical vectors); person 2 only in C.
    await _seed(db_session, [
        Face(photo_id=pa.id, embedding=faces_svc.to_blob(_vec(0)), det_score=0.95),
        Face(photo_id=pb.id, embedding=faces_svc.to_blob(_vec(0, jitter=0.15)), det_score=0.9),
        Face(photo_id=pc.id, embedding=faces_svc.to_blob(_vec(7)), det_score=0.92),
    ])

    summary = await face_clustering.assign_unclustered(db_session)
    assert summary["total_people"] == 2
    assert summary["clustered"] == 3

    # People list: 2 people, ordered by photo count (2 then 1).
    people = (await client.get("/api/people")).json()
    assert people["total"] == 2
    assert [p["photo_count"] for p in people["people"]] == [2, 1]

    big = people["people"][0]
    assert big["photo_count"] == 2

    # Name the bigger cluster — naming marks them "known".
    upd = (await client.patch(f"/api/people/{big['id']}", json={"name": "Mum"})).json()
    assert upd["name"] == "Mum" and upd["is_known"] is True

    # Its photos endpoint returns both photos.
    photos = (await client.get(f"/api/people/{big['id']}/photos")).json()
    assert photos["total"] == 2


async def test_trash_all_photos_of_a_person(client, db_session):
    pa, pc = await _seed(db_session, [
        _photo(file_path="/fake/p1.jpg"),
        _photo(file_path="/fake/p2.jpg"),
    ])
    await _seed(db_session, [
        Face(photo_id=pa.id, embedding=faces_svc.to_blob(_vec(0)), det_score=0.95),
        Face(photo_id=pc.id, embedding=faces_svc.to_blob(_vec(7)), det_score=0.92),
    ])
    await face_clustering.assign_unclustered(db_session)

    people = (await client.get("/api/people")).json()["people"]
    stranger = next(p for p in people if p["photo_count"] == 1)

    res = (await client.post(f"/api/people/{stranger['id']}/trash-photos")).json()
    assert res["deleted"] == 1 and res["batch"]

    # That photo is now in Trash; the library count drops, undo log exists.
    assert (await client.get("/api/photos")).json()["total"] == 1
    logs = (await client.get("/api/photos/cleanup-history")).json()["history"]
    assert any(l["reason"].startswith("person:") for l in logs)
