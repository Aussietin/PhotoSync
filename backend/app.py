import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from config import settings
from database import init_db
from routes import photos, tags, search, albums, stats, jobs, export


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    for d in (settings.UPLOAD_DIR, settings.THUMBNAIL_DIR, settings.PREVIEW_DIR):
        os.makedirs(d, exist_ok=True)
    from services.jobs import reap_stale_jobs
    await reap_stale_jobs()  # clear jobs left 'running' by a previous crash
    yield


app = FastAPI(title="PhotoSync API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def api_token_guard(request: Request, call_next):
    """If API_TOKEN is configured, require it on /api routes (health excepted)."""
    if settings.API_TOKEN and request.url.path.startswith("/api"):
        if request.url.path != "/api/health":
            if request.headers.get("X-API-Token") != settings.API_TOKEN:
                return JSONResponse({"detail": "Invalid or missing API token"}, status_code=401)
    return await call_next(request)


app.include_router(photos.router, prefix="/api/photos", tags=["photos"])
app.include_router(tags.router, prefix="/api/tags", tags=["tags"])
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(albums.router, prefix="/api/albums", tags=["albums"])
app.include_router(stats.router, prefix="/api/stats", tags=["stats"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(export.router, prefix="/api/export", tags=["export"])

app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
app.mount("/thumbnails", StaticFiles(directory=settings.THUMBNAIL_DIR), name="thumbnails")
app.mount("/previews", StaticFiles(directory=settings.PREVIEW_DIR), name="previews")


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}


@app.get("/api/server-info")
async def server_info():
    import socket
    local_ips: list[str] = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ips.append(s.getsockname()[0])
    except Exception:
        pass
    if not local_ips:
        local_ips = ["localhost"]
    return {"local_ips": local_ips, "frontend_port": 5173}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
