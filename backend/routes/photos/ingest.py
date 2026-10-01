"""Getting photos in: browser upload and in-place folder import."""
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
from routes.photos.serialize import _photo_fields
from services.storage import save_upload
from services.image_processor import process_photo
from services.deduplicator import find_duplicate
from utils.helpers import is_image, is_media, is_video, guess_mime

router = APIRouter()
logger = logging.getLogger("photosync")


# ── Upload ────────────────────────────────────────────────────────────────────

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_photos(
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    results = []
    for file in files:
        orig_name = file.filename or "photo.jpg"
        # Reject oversized uploads before writing anything to disk. Starlette
        # populates UploadFile.size for multipart parts.
        if file.size is not None and file.size > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"'{orig_name}' is {file.size // (1024 * 1024)} MB; "
                       f"limit is {settings.MAX_UPLOAD_SIZE_MB} MB.",
            )
        file_path, thumb_path, preview_path, file_size = await save_upload(file)
        # Videos have no image metadata/hash; track them for size-based culling.
        is_vid = is_video(orig_name)
        metadata = {} if is_vid else await process_photo(file_path, original_filename=orig_name)

        dup_id = None if is_vid else await find_duplicate(db, metadata.get("perceptual_hash"))

        photo = Photo(
            filename=file_path.name,
            original_filename=orig_name,
            file_path=str(file_path),
            thumbnail_path=str(thumb_path) if thumb_path else None,
            preview_path=str(preview_path) if preview_path else None,
            file_size=file_size,
            mime_type=file.content_type or guess_mime(orig_name),
            is_duplicate=dup_id is not None,
            duplicate_of_id=dup_id,
            **_photo_fields(metadata),
        )
        db.add(photo)
        await db.commit()
        await db.refresh(photo)
        results.append({"id": photo.id, "filename": photo.original_filename, "is_duplicate": photo.is_duplicate})

    return {"uploaded": len(results), "photos": results}


# ── Folder import ─────────────────────────────────────────────────────────────

class FolderImportIn(BaseModel):
    path: str
    recursive: bool = True


@router.post("/import-folder", status_code=status.HTTP_202_ACCEPTED)
async def import_folder(body: FolderImportIn):
    """Kick off a background import job. Poll GET /api/jobs/{id} for progress."""
    folder = Path(body.path)
    if not folder.exists() or not folder.is_dir():
        raise HTTPException(status_code=400, detail="Path does not exist or is not a directory")

    pattern = "**/*" if body.recursive else "*"
    files = [p for p in folder.glob(pattern) if p.is_file() and is_media(p.name)]

    async def runner(session: AsyncSession, job) -> dict:
        from services.storage import _make_thumbnail, _make_preview
        from services.deduplicator import rescan_duplicates
        import uuid

        job.total = len(files)
        await session.commit()

        known = set((await session.execute(select(Photo.file_path))).scalars().all())
        imported, skipped, failed = 0, 0, 0
        failures: list[dict] = []  # bounded sample surfaced in the job result

        for idx, file_path in enumerate(files):
            if str(file_path) in known:
                skipped += 1
            else:
                try:
                    if is_video(file_path.name):
                        # No frame decoder — index videos for size-based culling only.
                        session.add(Photo(
                            filename=file_path.name,
                            original_filename=file_path.name,
                            file_path=str(file_path),
                            file_size=file_path.stat().st_size,
                            mime_type=guess_mime(file_path.name),
                            **_photo_fields({}),
                        ))
                    else:
                        metadata = await process_photo(file_path, original_filename=file_path.name)
                        stem = uuid.uuid4().hex
                        thumb_path = await _make_thumbnail(file_path, stem)
                        preview_path = await _make_preview(file_path, stem)
                        session.add(Photo(
                            filename=file_path.name,
                            original_filename=file_path.name,
                            file_path=str(file_path),
                            thumbnail_path=str(thumb_path) if thumb_path else None,
                            preview_path=str(preview_path) if preview_path else None,
                            file_size=file_path.stat().st_size,
                            mime_type=guess_mime(file_path.name),
                            **_photo_fields(metadata),
                        ))
                    known.add(str(file_path))
                    imported += 1
                except Exception as exc:
                    # A single unreadable/locked/still-copying file must never abort
                    # the whole 20k-file job. Log it, count it, move on. It's NOT
                    # added to `known`, so re-running Import on this folder retries
                    # it automatically once it's actually readable.
                    logger.warning("Import failed for %s: %s", file_path, exc)
                    failed += 1
                    if len(failures) < 25:
                        failures.append({"filename": file_path.name, "error": str(exc)})

            # Commit + report progress in batches to keep the UI moving.
            if (idx + 1) % 50 == 0 or idx + 1 == len(files):
                job.processed = idx + 1
                await session.commit()

        dup_summary = await rescan_duplicates(session) if imported else {"duplicates": 0}
        return {
            "scanned": len(files),
            "imported": imported,
            "skipped": skipped,
            "failed": failed,
            "failed_files": failures,
            "duplicates_found": dup_summary.get("duplicates", 0),
        }

    from services.jobs import start_job
    job_id = await start_job("import", runner, total=len(files))
    return {"job_id": job_id, "files_found": len(files)}
