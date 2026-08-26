"""
Folder import — the practical ingestion path for a 20k-photo library.

These exercise the real background job (not mocked), which only works safely
because conftest.py's `client` fixture redirects services.jobs' DB session to
the same isolated in-memory DB as the rest of the test (see conftest.py).
Without that, these tests would write into the real on-disk photosync.db.
"""
import asyncio
import random

from PIL import Image

from services import jobs as jobs_service


async def _run_job_to_completion(client, job_id: int, timeout: float = 10.0) -> dict:
    """Wait for a background job to finish, then fetch its final state.

    Awaits the job's own asyncio task directly (services.jobs.wait_for_job)
    rather than polling GET /api/jobs/{id} in a loop. Polling would issue a
    concurrent request against the shared single-connection test DB while the
    job's own session is still mid-transaction — harmless in production (each
    request gets a real, independent DB connection) but it corrupts SQLAlchemy's
    identity map on the StaticPool-backed in-memory test DB. Awaiting the task
    directly sequences things properly: the job fully finishes (and its session
    fully closes) before this test touches the DB again.
    """
    await asyncio.wait_for(jobs_service.wait_for_job(job_id), timeout=timeout)
    return (await client.get(f"/api/jobs/{job_id}")).json()


def _make_jpeg(path, seed=0):
    """A small noisy JPEG — NOT a flat solid color. Perceptual hashing (phash)
    is DCT-based and discards the DC term, so any two flat/textureless images
    hash identically regardless of colour and get flagged as near-duplicates
    by the real dedup pass. Random per-pixel noise gives each file a distinct
    hash so import/count assertions aren't accidentally testing dedup instead."""
    rng = random.Random(seed)
    img = Image.new("RGB", (48, 48))
    img.putdata([(rng.randrange(256), rng.randrange(256), rng.randrange(256)) for _ in range(48 * 48)])
    img.save(path, "JPEG")


async def test_import_folder_basic_and_idempotent(client, tmp_path):
    _make_jpeg(tmp_path / "a.jpg", seed=1)
    _make_jpeg(tmp_path / "b.jpg", seed=2)
    (tmp_path / "clip.mp4").write_bytes(b"\x00" * 2048)  # fake video, tracked not decoded

    resp = await client.post(
        "/api/photos/import-folder", json={"path": str(tmp_path), "recursive": False}
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["files_found"] == 3

    job = await _run_job_to_completion(client, body["job_id"])
    assert job["status"] == "done"
    res = job["result"]
    assert res["scanned"] == 3
    assert res["imported"] == 3
    assert res["skipped"] == 0
    assert res["failed"] == 0

    listing = (await client.get("/api/photos")).json()
    assert listing["total"] == 3
    video = next(p for p in listing["photos"] if p["filename"] == "clip.mp4")
    assert video["is_video"] is True
    assert video["thumbnail_url"] is None

    # Re-importing the SAME folder must be a no-op (resumable/idempotent) —
    # every file is already known, nothing gets re-added or duplicated.
    resp2 = await client.post(
        "/api/photos/import-folder", json={"path": str(tmp_path), "recursive": False}
    )
    job2 = await _run_job_to_completion(client, resp2.json()["job_id"])
    res2 = job2["result"]
    assert res2["imported"] == 0
    assert res2["skipped"] == 3
    assert (await client.get("/api/photos")).json()["total"] == 3


async def test_import_folder_survives_one_bad_file(client, tmp_path, monkeypatch):
    """One unreadable/locked/corrupt file must not abort the whole job — this
    is the core guarantee for a real 20k-photo import."""
    _make_jpeg(tmp_path / "good1.jpg", seed=3)
    _make_jpeg(tmp_path / "bad.jpg", seed=4)
    _make_jpeg(tmp_path / "good2.jpg", seed=5)

    from routes import photos as photos_route

    real_process_photo = photos_route.process_photo

    async def flaky(path, original_filename=None):
        if path.name == "bad.jpg":
            raise RuntimeError("simulated locked/corrupt file")
        return await real_process_photo(path, original_filename=original_filename)

    monkeypatch.setattr(photos_route, "process_photo", flaky)

    resp = await client.post(
        "/api/photos/import-folder", json={"path": str(tmp_path), "recursive": False}
    )
    assert resp.json()["files_found"] == 3

    job = await _run_job_to_completion(client, resp.json()["job_id"])
    assert job["status"] == "done"  # one bad file must NOT error the whole job

    res = job["result"]
    assert res["scanned"] == 3
    assert res["imported"] == 2
    assert res["failed"] == 1
    assert res["failed_files"] == [{"filename": "bad.jpg", "error": "simulated locked/corrupt file"}]

    # The two good files actually made it into the library.
    listing = (await client.get("/api/photos")).json()
    assert listing["total"] == 2
    assert {p["filename"] for p in listing["photos"]} == {"good1.jpg", "good2.jpg"}

    # Re-running import (e.g. once the "locked" file is free) retries ONLY the
    # failed file — the two good ones are already known and correctly skipped.
    monkeypatch.undo()
    resp2 = await client.post(
        "/api/photos/import-folder", json={"path": str(tmp_path), "recursive": False}
    )
    job2 = await _run_job_to_completion(client, resp2.json()["job_id"])
    res2 = job2["result"]
    assert res2["imported"] == 1   # bad.jpg, now readable
    assert res2["skipped"] == 2    # good1.jpg, good2.jpg
    assert res2["failed"] == 0
    assert (await client.get("/api/photos")).json()["total"] == 3


async def test_import_folder_rejects_bad_path(client):
    resp = await client.post(
        "/api/photos/import-folder", json={"path": "/definitely/not/a/real/path", "recursive": True}
    )
    assert resp.status_code == 400
