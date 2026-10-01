"""Background library analysis: flags, quality, previews, AI tags, faces, dupes."""
import json
import logging
import os
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from starlette.background import BackgroundTask
from sqlalchemy import select, func, update, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import settings
from database import get_db
from models.photo import Photo, DeletionLog

router = APIRouter()


# ── Library analysis (rescan flags for existing photos) ─────────────────────────

@router.post("/analyze", status_code=status.HTTP_202_ACCEPTED)
async def analyze_library(
    recompute_quality: bool = Query(True),
    ai_tagging: bool = Query(True, description="Run local CLIP tagging + embeddings"),
    face_grouping: bool = Query(True, description="Detect + cluster faces into people"),
    reanalyze: bool = Query(False, description="Re-tag photos that already have AI tags"),
):
    """Background one-shot analysis: screenshot flags, quality scores, exposure/
    resolution classification, missing previews, near-duplicate clustering,
    burst grouping, and local CLIP tagging + embeddings for semantic search.
    Poll GET /api/jobs/{id}. Run once after a bulk import."""

    async def runner(session: AsyncSession, job) -> dict:
        from services.screenshot_detector import detect_screenshot
        from services.image_processor import recompute_quality as recompute_quality_fn, _classify
        from services.storage import _make_preview
        from services.deduplicator import rescan_duplicates
        from services.bursts import group_bursts
        from services.ai_tagger import tag_photos_batch
        from services import embeddings, faces
        from services import face_clustering
        from models.photo import Face
        from sqlalchemy.orm import selectinload
        import uuid

        photos = (await session.execute(
            select(Photo).where(Photo.deleted_at.is_(None))
            .options(selectinload(Photo.tags))
        )).scalars().all()
        job.total = len(photos)
        await session.commit()

        clip_available = ai_tagging and embeddings.is_available()
        face_available = face_grouping and faces.is_available()
        # Photos already face-scanned, so re-runs only process new ones.
        faces_done: set[int] = set((await session.execute(
            select(Face.photo_id).distinct()
        )).scalars().all()) if face_available else set()
        screenshots_flagged = quality_updated = previews_made = ai_tagged = faces_found = 0
        # Photos needing AI tagging are buffered and flushed in batches so the
        # CLIP model runs one call per batch instead of once per photo — far
        # fewer Python/GIL round-trips over a 20k-photo pass.
        AI_BATCH_SIZE = 16
        ai_batch: list[Photo] = []

        async def _flush_ai_batch() -> None:
            nonlocal ai_tagged
            if ai_batch:
                ai_tagged += await tag_photos_batch(session, ai_batch)
                ai_batch.clear()

        for idx, photo in enumerate(photos):
            if (photo.mime_type or "").startswith("video/"):
                # Videos have no decodable frames here — nothing to analyze.
                if (idx + 1) % 50 == 0 or idx + 1 == len(photos):
                    job.processed = idx + 1
                    await session.commit()
                continue
            photo.is_screenshot = detect_screenshot(
                width=photo.width, height=photo.height,
                camera_make=photo.camera_make, original_filename=photo.original_filename,
            )
            if photo.is_screenshot:
                screenshots_flagged += 1

            # Backfill a web preview if missing and we still have the original.
            if not photo.preview_path and photo.file_path and Path(photo.file_path).exists():
                pv = await _make_preview(Path(photo.file_path), uuid.uuid4().hex)
                if pv:
                    photo.preview_path = str(pv)
                    previews_made += 1

            src = photo.thumbnail_path or photo.file_path
            if src and Path(src).exists():
                flags = _classify(src, photo.width, photo.height)
                photo.is_dark = flags["is_dark"]
                photo.is_overexposed = flags["is_overexposed"]
                photo.is_low_res = flags["is_low_res"]
                if recompute_quality:
                    score = recompute_quality_fn(src)
                    if score is not None:
                        photo.quality_score = score
                        quality_updated += 1

            # Local CLIP tagging + embedding. Re-tag when forced, when the photo
            # has no tags yet, or (model now present) when it lacks an embedding —
            # so heuristic-only photos get upgraded once the model is installed.
            # Buffered and encoded in batches (see AI_BATCH_SIZE above).
            if ai_tagging:
                needs_ai = reanalyze or not photo.ai_tags or (
                    clip_available and photo.clip_embedding is None
                )
                if needs_ai:
                    ai_batch.append(photo)
                    if len(ai_batch) >= AI_BATCH_SIZE:
                        await _flush_ai_batch()

            # Local face detection + embedding (clustered into people after the loop).
            if face_available and (reanalyze or photo.id not in faces_done):
                faces_found += await face_clustering.index_photo_faces(session, photo)

            if (idx + 1) % 50 == 0 or idx + 1 == len(photos):
                job.processed = idx + 1
                await session.commit()

        await _flush_ai_batch()

        dup_summary = await rescan_duplicates(session)
        burst_summary = await group_bursts(session)
        face_summary = await face_clustering.assign_unclustered(session) if face_available else None

        return {
            "scanned": len(photos),
            "screenshots": screenshots_flagged,
            "quality_recomputed": quality_updated,
            "previews_made": previews_made,
            "ai_tagged": ai_tagged,
            "clip_model_available": clip_available,
            "faces_found": faces_found,
            "face_model_available": face_available,
            "people": face_summary,
            "duplicates": dup_summary,
            "bursts": burst_summary,
        }

    from services.jobs import start_job
    job_id = await start_job("analyze", runner)
    return {"job_id": job_id}


@router.post("/rescan-duplicates", status_code=status.HTTP_202_ACCEPTED)
async def rescan_duplicates_endpoint():
    """Re-cluster near-duplicates across the whole library (background BK-tree)."""
    async def runner(session: AsyncSession, job) -> dict:
        from services.deduplicator import rescan_duplicates
        return await rescan_duplicates(session)

    from services.jobs import start_job
    job_id = await start_job("rescan-duplicates", runner)
    return {"job_id": job_id}


@router.post("/scan-screenshots")
async def scan_screenshots(db: AsyncSession = Depends(get_db)):
    """Retroactively run screenshot detection on all un-scanned photos."""
    from services.screenshot_detector import detect_screenshot

    result = await db.execute(select(Photo).where(Photo.deleted_at.is_(None)))
    photos = result.scalars().all()
    updated = 0
    for photo in photos:
        detected = detect_screenshot(
            width=photo.width,
            height=photo.height,
            camera_make=photo.camera_make,
            original_filename=photo.original_filename,
        )
        if detected != photo.is_screenshot:
            photo.is_screenshot = detected
            updated += 1
    await db.commit()
    total_screenshots = sum(1 for p in photos if p.is_screenshot)
    return {"scanned": len(photos), "updated": updated, "total_screenshots": total_screenshots}
