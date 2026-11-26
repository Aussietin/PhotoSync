"""/api/photos, split by concern (was one 1,183-line module).

Order matters: FastAPI matches routes in registration order, and items.py's
`/{photo_id}` must come after every fixed path.
"""
from fastapi import APIRouter

from routes.photos import analysis, cleanup, ingest, items, library
from routes.photos.cleanup import sweep_expired_trash  # noqa: F401 -- app.py lifespan
from routes.photos.serialize import _photo_fields, _serialize, _tok  # noqa: F401 -- albums/people/search

router = APIRouter()
# Merge route lists rather than include_router(): list_photos lives at "" (so
# the URL stays /api/photos, no trailing-slash redirect), and include_router
# refuses an empty prefix + empty path.
for _module in (ingest, library, cleanup, analysis, items):
    router.routes.extend(_module.router.routes)
