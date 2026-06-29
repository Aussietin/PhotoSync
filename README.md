# PhotoSync

A Python-powered photo organizer with a responsive web interface, built to manage large photo libraries (20,000+ photos) from iPhone.

## Features

- **Auto-tagging** — AI/ML-based image tagging using scene and object detection
- **Duplicate detection** — Perceptual hashing to find and remove duplicates
- **Timeline view** — Browse photos chronologically by date taken (EXIF)
- **Smart search** — Search by tags, dates, objects, and metadata
- **Batch operations** — Select and act on multiple photos at once
- **Mobile-first UI** — Responsive interface accessible from iPhone browser

## Architecture

```
PhotoSync/
├── backend/          # Python FastAPI server
│   ├── app.py        # App entry point
│   ├── config.py     # Configuration
│   ├── database.py   # DB setup (SQLite via SQLAlchemy)
│   ├── models/       # SQLAlchemy models
│   ├── routes/       # API route handlers
│   ├── services/     # Business logic (processing, AI, dedup, storage)
│   └── utils/        # Shared helpers
└── frontend/         # Vue 3 + Vite web app
    └── src/
        ├── components/  # Reusable UI components
        ├── views/       # Page-level views
        ├── api/         # API client
        └── router/      # Vue Router config
```

## Tech Stack

| Layer | Tech |
|-------|------|
| Backend | Python 3.10+, FastAPI, SQLAlchemy, SQLite |
| Image processing | Pillow, imagehash, exifread |
| AI tagging | CLIP / transformers (pluggable) |
| Frontend | Vue 3, Vite, Tailwind CSS |
| Dev tooling | uvicorn, eslint, prettier |

## Quick Start

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
# API available at http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# UI available at http://localhost:5173
```

### Network access from iPhone

The backend defaults to `127.0.0.1` (localhost only). To use PhotoSync from your phone:

1. Create `backend/.env` with a strong token and network binding:
   ```
   API_TOKEN=choose-a-long-random-secret
   HOST=0.0.0.0
   ```
2. Start the backend (`python app.py`) and the frontend with `npm run dev -- --host`.
3. Navigate to `http://<your-mac-local-ip>:5173` in your iPhone browser.

**Security note:** Never set `HOST=0.0.0.0` without also setting `API_TOKEN`. Without a token, anyone on the same Wi-Fi network can access your photos. With a token set, all routes — including image files — require it.

## API Overview

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/photos/upload` | Upload one or more photos |
| `GET` | `/api/photos` | List photos (pagination, filters) |
| `GET` | `/api/photos/{id}` | Get single photo metadata |
| `DELETE` | `/api/photos/{id}` | Delete a photo |
| `GET` | `/api/photos/{id}/thumbnail` | Serve thumbnail |
| `GET` | `/api/photos/timeline` | Photos grouped by date |
| `GET` | `/api/tags` | List all tags |
| `POST` | `/api/tags/{photo_id}` | Add tag to photo |
| `GET` | `/api/search` | Search photos |
| `GET` | `/api/photos/duplicates` | List duplicate groups |

## Roadmap

- [ ] Face recognition clustering
- [ ] Quality scoring (blur, exposure)
- [ ] Album / collection management
- [ ] Cloud backup integration (iCloud, S3)
- [ ] Sharing links

## License

MIT
