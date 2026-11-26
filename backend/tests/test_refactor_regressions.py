"""Regressions found in the 2026-10 refactor pass. Each failed on the
pre-refactor code (c863989, PR #31 head)."""
import asyncio
import io
import time
from datetime import datetime
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from config import settings
from models.photo import Photo


async def _seed(session, *photos):
    for p in photos:
        session.add(p)
    await session.commit()
    return photos


def _photo(name="a.jpg", **kw):
    return Photo(filename=name, original_filename=name, file_path=f"/nowhere/{name}",
                 file_size=1, mime_type="image/jpeg", **kw)


async def test_tests_never_write_into_the_real_media_dirs():
    """Uploads in tests landed in backend/uploads -- the real local library
    (20 zero/11-byte test files had piled up there by 2026-10-01)."""
    backend = Path(__file__).parent.parent.resolve()
    for d in (settings.UPLOAD_DIR, settings.THUMBNAIL_DIR, settings.PREVIEW_DIR, settings.FACE_DIR):
        assert not Path(d).resolve().is_relative_to(backend), d


async def test_permanent_delete_requires_the_photo_to_be_in_trash(client, db_session):
    """DELETE /{id}/permanent skipped trash entirely: one call took a live
    photo straight to gone (and its uploaded file with it)."""
    (p,) = await _seed(db_session, _photo())
    resp = await client.delete(f"/api/photos/{p.id}/permanent")
    assert resp.status_code == 409
    assert (await client.get(f"/api/photos/{p.id}")).status_code == 200


async def test_undo_does_not_resurrect_a_photo_trashed_again_by_hand(client, db_session):
    """deleted_batch was never cleared: cleanup -> restore -> manual trash ->
    'undo cleanup' brought back a photo the user had deliberately trashed."""
    (p,) = await _seed(db_session, _photo(is_screenshot=True))
    batch = (await client.post("/api/photos/cleanup", json={"screenshots": True})).json()["batch"]
    await client.post(f"/api/photos/{p.id}/restore")
    await client.post("/api/photos/bulk/delete", json={"photo_ids": [p.id]})

    await client.post(f"/api/photos/undo-cleanup/{batch}")
    assert (await client.get(f"/api/photos/{p.id}")).json()["deleted_at"] is not None


async def test_upload_rejects_non_media_files(client):
    """Any extension was accepted and then served same-origin from /uploads
    (an .html upload is stored XSS)."""
    files = {"files": ("evil.html", io.BytesIO(b"<script>alert(1)</script>"), "text/html")}
    resp = await client.post("/api/photos/upload", files=files)
    assert resp.status_code == 415


async def test_slow_image_work_does_not_block_the_event_loop(client, monkeypatch):
    """Thumbnail/preview/metadata work is sync PIL inside async functions, so an
    upload (or a 20k-photo import/analyze job) froze every other request."""
    import services.storage as storage

    def slow_downscale(*a, **kw):
        time.sleep(0.6)
        return None

    monkeypatch.setattr(storage, "_downscale_jpeg", slow_downscale)
    import app as app_module

    async def scenario() -> float:
        async with AsyncClient(transport=ASGITransport(app=app_module.app), base_url="http://t") as c2:
            t0 = time.perf_counter()
            files = {"files": ("a.jpg", io.BytesIO(b"not really a jpeg"), "image/jpeg")}
            upload = asyncio.create_task(client.post("/api/photos/upload", files=files))
            await asyncio.sleep(0.1)
            r = await c2.get("/api/health")
            elapsed = time.perf_counter() - t0
            assert r.status_code == 200
            await upload
            return elapsed

    assert await scenario() < 0.5
