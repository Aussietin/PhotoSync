"""
Lightweight in-process background jobs.

Long operations (import, analyze, rescan) would exceed HTTP timeouts and block
the worker if run inline. ``start_job`` records a Job row, returns its id
immediately, and runs the work in a fire-and-forget asyncio task that updates
progress in the DB so the client can poll ``GET /api/jobs/{id}``.

This is deliberately simple (no Celery/Redis): fine for a single-user,
single-worker local tool. The trade-off is that an interrupted process leaves
jobs marked running — ``reap_stale_jobs`` cleans those up on startup.
"""
import asyncio
import json
import traceback
from datetime import datetime
from typing import Awaitable, Callable

from sqlalchemy import select, update

from database import AsyncSessionLocal
from models.photo import Job

# runner(session, job) -> dict result; runner updates job.processed as it goes.
JobRunner = Callable[["AsyncSession", Job], Awaitable[dict]]


async def start_job(kind: str, runner: JobRunner, total: int = 0) -> int:
    """Create a Job, schedule it on the event loop, return the job id."""
    async with AsyncSessionLocal() as session:
        job = Job(kind=kind, status="pending", total=total)
        session.add(job)
        await session.commit()
        await session.refresh(job)
        job_id = job.id

    asyncio.create_task(_run(job_id, runner))
    return job_id


async def _run(job_id: int, runner: JobRunner) -> None:
    async with AsyncSessionLocal() as session:
        job = await session.get(Job, job_id)
        if job is None:
            return
        job.status = "running"
        await session.commit()
        try:
            result = await runner(session, job)
            job.result = json.dumps(result or {})
            job.status = "done"
            job.message = "Completed"
        except Exception as exc:  # noqa: BLE001 — record any failure for the UI
            job.error = f"{exc}\n{traceback.format_exc()}"
            job.status = "error"
            job.message = str(exc)
        finally:
            job.finished_at = datetime.utcnow()
            await session.commit()


async def reap_stale_jobs() -> None:
    """Mark any jobs left 'running'/'pending' by a crash as errored (run at startup)."""
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(Job)
            .where(Job.status.in_(["running", "pending"]))
            .values(status="error", message="Interrupted by server restart",
                    finished_at=datetime.utcnow())
        )
        await session.commit()


def serialize_job(job: Job) -> dict:
    pct = round(job.processed / job.total * 100, 1) if job.total else None
    return {
        "id": job.id,
        "kind": job.kind,
        "status": job.status,
        "total": job.total,
        "processed": job.processed,
        "percent": pct,
        "message": job.message,
        "result": json.loads(job.result) if job.result else None,
        "error": job.error,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
    }
