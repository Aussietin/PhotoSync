# PhotoSync — Project Knowledge

A living record of goals, architecture decisions, hard-won learnings, and the
development roadmap. Update this as the project evolves.

---

## The problem we're solving

Clean a ~20,000-photo iPhone camera roll: remove screenshots you don't need,
collapse duplicates and bursts, drop blurry/low-quality shots, and organise the
keepers — using a Python backend with a responsive web UI usable from the phone.

### The one constraint that shapes everything

**A web app cannot delete photos from the iOS camera roll.** Only a native app
using the Photos framework (with user permission) can. So PhotoSync cannot
"clean your phone" directly. The realistic workflows are:

1. **Archive-and-replace (recommended):** export the whole roll to the machine
   running PhotoSync (Finder / Image Capture / iCloud download), clean it here,
   treat the cleaned library as the new master, then wipe/re-sync the phone.
2. **Deletion plan:** PhotoSync produces a list of what to delete; you act on it
   on the phone manually or via an iOS Shortcut.

Everything in the roadmap is oriented around making one of these loops smooth.
This is the gap between "cleans photos" and "solves my problem" — see Stage 2.

---

## Architecture

- **Backend:** FastAPI + async SQLAlchemy + SQLite. Image work via Pillow,
  imagehash (perceptual hash), exifread, numpy. Files on disk under
  `backend/uploads`, thumbnails under `backend/thumbnails`.
- **Frontend:** Vue 3 + Vite + Tailwind, mobile-first. Leaflet for the map.
- **Ingestion paths:** (a) browser upload, one file per request; (b) server-side
  **folder import** — point at a directory the photos were dumped into. Folder
  import is the only practical path for 20k files.

### Key data model fields (`backend/models/photo.py`)
`is_screenshot`, `is_duplicate` + `duplicate_of_id`, `quality_score`,
`is_favorite`, `deleted_at` (soft delete), plus EXIF (`taken_at`, camera, GPS)
and `perceptual_hash`. Albums via a many-to-many junction.

---

## Decisions & rationale

- **Soft delete (`deleted_at`) + Trash.** Cleanup is destructive and users second-
  guess; nothing is hard-deleted until explicitly emptied. Restore is cheap.
- **Duplicate detection is two-tier.** Per-upload does only an *indexed exact*
  hash match (flat cost). *Near*-duplicate clustering is a **batch BK-tree pass**
  (`rescan_duplicates`) run after import / on demand — ~O(n log n) instead of the
  original O(n²) per-upload scan. Clusters are quality-ordered so the sharpest
  shot is kept as the original.
- **Quality score = variance-of-Laplacian (sharpness) + exposure**, pure numpy,
  computed on a 512px downscale so scores compare across resolutions and stay
  fast. Drives low-quality triage, quality sort, and which duplicate to suggest.
- **Screenshot detection by exact screen dimensions** (20+ iPhone/iPad sizes) +
  filename keywords. No file read needed, so it's instant to re-scan.
- **Mass cleanup is server-side and filter-based.** `POST /photos/cleanup` trashes
  *every* photo matching selected categories in one SQL UPDATE — never relies on
  what the client has loaded. Favorites are always protected.

---

## Learnings / gotchas (mistakes already fixed — don't reintroduce)

- **HEIC is the default iPhone format.** Pillow can't open HEIF without
  `pillow-heif`. Without it, every iPhone photo silently failed processing (no
  thumbnail, dimensions, screenshot/quality detection). Fixed by
  `services/heif_support.py` registering the opener; dependency pinned.
  *Still TODO:* desktop browsers can't render HEIC in the full-size modal — need
  a web-friendly JPEG preview, not just the thumbnail (Stage 1).
- **`scipy` was imported but never declared** in requirements, so blur detection
  failed silently and every photo got a constant sharpness. Rewrote in pure
  numpy. Lesson: a bare `except` that hides an ImportError makes a core feature a
  no-op — prefer narrow excepts and declare every import.
- **O(n²) duplicate scan** would have taken hours on 20k. See two-tier design.
- **"Delete all" mapped the paginated client buffer**, so it deleted only what was
  scrolled into view. Mass actions must be server-side filter-based.
- **ZIP export builds the whole archive in memory** and caps at 500 photos — fine
  for small selections, needs streaming for full-library export (Stage 2).
- **Long operations run synchronously in the request** (import, analyze). At 20k
  these will exceed HTTP timeouts and block the worker — needs background jobs
  (Stage 1).

---

## Roadmap

### Stage 1 — Make ingestion work at 20k ✅
- [x] HEIC/HEIF support via pillow-heif.
- [x] Single-commit folder import + auto duplicate clustering after import.
- [x] Background jobs + progress (Job model, `services/jobs.py`, `/api/jobs`);
      import/analyze/rescan run off the request thread with progress polling.
- [x] Web-friendly JPEG previews so HEIC originals display in-browser.
- [ ] Document the Finder/Image Capture "dump to folder" workflow (in ExportView UI).
- [ ] Resumable/parallel browser upload (folder import is the practical path for now).

### Stage 2 — Close the loop with the iPhone ✅
- [x] Streaming keeper export (built on disk, year/month folders, no 500 cap).
- [x] Deletion-plan export (CSV/JSON of trashed photos + reasons).
- [x] In-app archive-and-replace guidance (ExportView).
- [ ] Actual iOS Shortcut recipe to consume the deletion plan (doc/asset).

### Stage 3 — Make cleanup genuinely "smart" — partial
- [x] Burst grouping by capture-time proximity + visual similarity (keep-the-best).
- [x] More cull categories: dark, overexposed, low-res (wired into cleanup).
- [x] **Memes/received images**: no-EXIF + not-screenshot filter catches WhatsApp
      forwards, meme downloads, etc. Pure SQL condition, no new DB column.
- [ ] Documents/receipts category (future).
- [ ] **Real AI tagging + semantic search** (still the color-heuristic placeholder;
      needs an embedding model — deferred, can't validate a model in this env).
- [ ] Face grouping (future).

### Stage 4 — Safety, trust & polish ✅
- [x] Tests: screenshot detector + BK-tree clustering + 36 integration tests
      covering cleanup, undo, meme filter, photo CRUD, bulk ops (all green).
- [x] **Alembic migrations**: `init_db()` runs `alembic upgrade head` on startup.
      `manage.py` helper for makemigration/stamp/history. Existing DBs: run
      `python manage.py stamp` once, then future migrations apply cleanly.
- [x] Trash retention/auto-empty (`/empty-trash?older_than_days=`), deletion audit
      log (`DeletionLog`), undo-last-cleanup (batch token + `/undo-cleanup`).
- [x] Optional API token auth (`API_TOKEN` env → `X-API-Token`).
- [x] **iOS Shortcut recipe** documented in ExportView (step-by-step using the
      Shortcuts app + deletion-plan CSV to delete culled photos on the phone).

### Bug fixes shipped (were silent production failures, caught by tests)
- Route shadowing: `GET /cleanup-summary`, `/cleanup-history`, `/screenshots`,
  `/burst-groups`, `/duplicate-groups`, `/triage-queue`, `POST /bulk/favorite`,
  `POST /bulk/restore` all returned 422 because they were registered after
  parameterized `/{photo_id}` routes. Fixed by moving `/{photo_id}` routes last.
- `GET /trash` missing `selectinload(Photo.tags)` → `MissingGreenlet` crash for
  trashed photos with tags (async lazy-load not supported in SQLAlchemy 2.x).
- `POST /undo-cleanup/{batch}` returned 200 for unknown batch tokens; now 404.

### Known gaps / next
- Real semantic search + AI tagging (embedding model — CLIP/ONNX).
- `download-zip` (small selections) is still in-memory; keeper export is the
  scalable path for large exports.
