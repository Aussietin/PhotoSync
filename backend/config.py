from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    APP_NAME: str = "PhotoSync"
    DATABASE_URL: str = "sqlite+aiosqlite:///./photosync.db"
    UPLOAD_DIR: str = str(Path(__file__).parent / "uploads")
    THUMBNAIL_DIR: str = str(Path(__file__).parent / "thumbnails")
    PREVIEW_DIR: str = str(Path(__file__).parent / "previews")
    THUMBNAIL_SIZE: tuple[int, int] = (400, 400)
    PREVIEW_SIZE: tuple[int, int] = (1600, 1600)  # web-friendly JPEG for the viewer
    MAX_UPLOAD_SIZE_MB: int = 50
    # Allowed browser origins, comma-separated. Override in .env, e.g.
    #   CORS_ORIGINS=http://localhost:5173,http://192.168.1.20:5173
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins(self) -> list[str]:
        """CORS_ORIGINS parsed into a list for the CORS middleware."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # Quality/classification thresholds (0–1 brightness scale)
    DARK_THRESHOLD: float = 0.18
    OVEREXPOSED_THRESHOLD: float = 0.92
    LOW_RES_MEGAPIXELS: float = 0.5  # below this is "low res"

    # Files at or above this size are flagged "large" — mostly videos and the
    # occasional ProRAW/panorama. These are the biggest space hogs in a camera
    # roll, so they get their own cull category and badge.
    LARGE_FILE_MB: int = 25

    # Trash retention: photos in trash older than this are eligible for auto-empty
    TRASH_RETENTION_DAYS: int = 30

    # SAFETY: when False (default), emptying Trash / permanent-delete only removes
    # files PhotoSync itself copied into uploads/ — it never deletes a folder-
    # imported *original* that lives elsewhere on disk. Keep this False unless your
    # imported folder is a throwaway copy you intend to cull destructively.
    DELETE_IN_PLACE_ORIGINALS: bool = False

    # Optional API token. When set (non-empty), all /api routes require
    # `X-API-Token: <token>`. Empty = open (default, for localhost use).
    API_TOKEN: str = ""

    # ── Local AI (CLIP) ──────────────────────────────────────────────────────
    # Semantic search + zero-shot tagging run fully on-device via a local CLIP
    # model — no data ever leaves the machine, no API key, no cost. The model is
    # an OPTIONAL dependency (pip install -r requirements-ai.txt). If it isn't
    # installed the app still runs and tagging falls back to the colour heuristic.
    # Vision model for semantic search + zero-shot tagging. Swap to a stronger
    # local model for sharper results (slower to index on CPU), e.g.
    #   clip-ViT-L-14      — bigger CLIP, noticeably better retrieval
    # Both are sentence-transformers ids and run fully on-device.
    CLIP_MODEL: str = "clip-ViT-B-32"
    # A zero-shot tag is kept when image↔label cosine similarity exceeds this.
    AI_TAG_THRESHOLD: float = 0.22
    AI_MAX_TAGS: int = 8

    # ── Local face recognition (InsightFace / ArcFace) ───────────────────────
    # Detect + embed faces, cluster into people, so you can name who you know and
    # bulk-cull everyone you don't. Fully on-device, optional dependency
    # (pip install -r requirements-ai.txt). If unavailable, face features are off.
    FACE_MODEL: str = "buffalo_l"          # InsightFace model pack (~300MB once)
    FACE_MIN_DET_SCORE: float = 0.60       # ignore weak/uncertain detections
    FACE_MATCH_THRESHOLD: float = 0.45     # cosine sim to merge a face into a person
    FACE_MIN_SIZE: int = 40                # ignore tiny faces (px, longest side)
    FACE_DIR: str = str(Path(__file__).parent / "faces")  # cropped face thumbnails

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
