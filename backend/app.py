import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from database import init_db
from routes import photos, tags, search


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

# Serve uploaded originals and thumbnails
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
app.mount("/thumbnails", StaticFiles(directory=settings.THUMBNAIL_DIR), name="thumbnails")


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
