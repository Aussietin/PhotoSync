import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from database import init_db
from routes import photos, tags, search, albums, stats


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.THUMBNAIL_DIR, exist_ok=True)
    yield


app = FastAPI(title="PhotoSync API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(photos.router, prefix="/api/photos", tags=["photos"])
app.include_router(tags.router, prefix="/api/tags", tags=["tags"])
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(albums.router, prefix="/api/albums", tags=["albums"])
app.include_router(stats.router, prefix="/api/stats", tags=["stats"])

app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
app.mount("/thumbnails", StaticFiles(directory=settings.THUMBNAIL_DIR), name="thumbnails")


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
