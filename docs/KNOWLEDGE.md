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

### Stage 1 — Make ingestion work at 20k (current blockers)
- [x] HEIC/HEIF support via pillow-heif.
- [x] Single-commit folder import + auto duplicate clustering after import.
- [ ] **Background jobs + progress.** Move import/analyze/rescan off the request
      thread (asyncio task + a job-status table + polling endpoint); show progress
      in the UI. Without this, 20k will time out.
- [ ] **Web-friendly previews** (medium JPEG) so HEIC originals display in-browser.
- [ ] Document the Finder/Image Capture "dump to folder" ingestion workflow.

### Stage 2 — Close the loop with the iPhone (what actually "solves" it)
- [ ] **Streaming keeper export** — unlimited, structured by date/album, not
      in-memory.
- [ ] **Deletion-plan export** (CSV/JSON of filenames to delete) + an iOS Shortcut
      recipe to consume it.
- [ ] In-app guidance for the archive-and-replace workflow.

### Stage 3 — Make cleanup genuinely "smart"
- [ ] **Burst grouping** by capture-time proximity + visual similarity
      ("8 near-identical shots → keep the sharpest").
- [ ] More cull categories: dark, overexposed, tiny/low-res, memes/received
      images (no EXIF + messaging-app dimensions), documents/receipts.
- [ ] **Real AI tagging + semantic search** (replace the color-heuristic
      placeholder) so you can find-and-cull by content.
- [ ] Face grouping to keep/cull by person (future).

### Stage 4 — Safety, trust & polish
- [ ] **Tests.** Currently zero; for software that deletes photos this is the top
      risk. Cover dedup/screenshot/quality/cleanup-filter logic + API.
- [ ] Trash retention / auto-empty after N days; deletion audit log;
      "undo last cleanup" (batch restore).
- [ ] Auth before exposing beyond localhost.
