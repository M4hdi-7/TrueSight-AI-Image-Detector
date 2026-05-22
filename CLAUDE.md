# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project Overview

**TrueSight v1.1** is a local-network web app that classifies images as AI-generated, deepfake, or authentic. It is a thin orchestrator around **Hive AI's V3 detection API** with added local forensic signals (EXIF, JPEG quantization, dimension checks) and a local SQLite history.

Earlier versions bundled a 5-model "jury" of local ML models. v1.1 removed that — there is **no torch/transformers/ONNX** in this codebase. All detection runs via the Hive API.

- Backend: Flask (port 5000)
- Frontend: Vanilla HTML/CSS/JS, served with `python -m http.server` (port 8000)
- Storage: SQLite (`backend/history.db`) + uploaded images on disk
- Target deployment: LAN only (no auth, no HTTPS)

## Repository Layout

```
backend/
  app.py              # Flask app — routes, DB, upload handling
  ai_model/
    __init__.py
    model.py          # predict_image() — orchestrates Hive + EXIF + reasons
    hive_client.py    # HTTP wrapper around Hive V3 API
  requirements.txt
  verify_hive.py      # Manual smoke test for Hive credentials (NOT a pytest suite)
  history.db          # SQLite — single `history` table
  uploads/            # UUID-named user images
  .env                # HIVE_API_KEY lives here (gitignored going forward)
frontend/
  index.html          # Single-page app shell
  script.js           # ~650 lines, flat — all UI logic
  style.css           # ~1400 lines, light/dark theming via CSS vars
  manifest.json       # PWA manifest
  *.png / *.ico       # App icons
Test/                 # Sample images for manual testing — NOT automated tests
start.bat             # Windows launcher (detects LAN IP, opens two CMD windows)
README.md             # User-facing setup docs
```

## Common Commands

### First-time setup
```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
# Create backend/.env with: HIVE_API_KEY=<your_key>
```

### Run the app
```powershell
# From repo root — opens backend (5000) + frontend (8000) in separate windows
.\start.bat
```

Or manually:
```powershell
# Backend
cd backend ; venv\Scripts\python.exe app.py
# Frontend (separate shell)
cd frontend ; python -m http.server 8000
```

### Verify Hive credentials
```powershell
cd backend ; venv\Scripts\python.exe verify_hive.py
```

### Enable Flask debug
```powershell
$env:FLASK_DEBUG = "true"
```

## Architecture & Data Flow

```
User picks image
  → frontend/script.js validates type + size (200 MB cap)
  → POST /predict (multipart, field name: "image")
    → app.py: extension whitelist → secure_filename → UUID rename → file.save()
    → PIL Image.open() magic-byte check (deletes file on failure)
    → ai_model.model.predict_image(path)
        → reads EXIF + JPEG quantization
        → rejects images > 8000px per side
        → hive_client.classify_image(path) — 60 s timeout
        → parses Hive response → (label, confidence, reasons, signals, metadata)
    → INSERT INTO history (...)
    → JSON response: {verdict, score, reasons, metadata, filename, signals}
  → frontend renders verdict card, signals breakdown, EXIF grid
  → history tab pulls last 50 via GET /history
```

## API Surface

All routes defined in [backend/app.py](backend/app.py):

| Route                   | Method | Purpose                                  |
| ----------------------- | ------ | ---------------------------------------- |
| `/predict`              | POST   | Analyze an uploaded image                |
| `/history`              | GET    | Return last 50 scans (newest first)      |
| `/clear_history`        | DELETE | Wipe `history` table + `uploads/` dir    |
| `/uploads/<filename>`   | GET    | Serve a stored image                     |

Cache headers: API responses are forced `no-store`; `/uploads/*` is left cacheable (immutable UUID filenames). See [app.py:177-184](backend/app.py#L177-L184).

## Database

Single table, created at startup in [app.py:32-46](backend/app.py#L32-L46):

```sql
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    result TEXT NOT NULL,
    confidence REAL,
    reasons TEXT,          -- JSON-serialized list of strings
    timestamp TEXT         -- "YYYY-MM-DD HH:MM"
)
```

All queries are parameterized. No indexes (not needed at 50-row read cap).

## Frontend Conventions

- **No framework, no build step.** Edit `index.html` / `script.js` / `style.css` directly.
- **State** lives in module-level vars in `script.js`: `currentAnalysis`, `lastHistoryJson`, drag/focus trackers.
- **API base URL** is computed from `window.location.hostname` so phones on LAN can hit the PC's backend — do not hardcode `localhost`.
- **Theme** is toggled via a `data-theme` attribute on `<html>` and persisted in `localStorage` under key `theme`.
- **Escaping**: use `textContent` / `escapeHTML()` helper for any user-derived or Hive-derived strings. Never use `innerHTML` with unsanitized input.
- **Accessibility is load-bearing here** — ARIA roles, focus traps in modals, `:focus-visible`, keyboard activation, `prefers-reduced-motion`. Preserve these when editing.

## Configuration & Secrets

- `HIVE_API_KEY` is loaded from `backend/.env` via `python-dotenv` ([app.py:2-3](backend/app.py#L2-L3)).
- `FLASK_DEBUG` env var toggles debug mode (default off).
- No other config surface. Constants like `MAX_FILE_SIZE` (200 MB), `ALLOWED_EXTENSIONS`, and the 8000 px dimension cap are hardcoded.

**Do not commit `.env`.** If you see a Hive key in the diff, stop and flag it.

## Validation Layers (don't weaken these)

1. Frontend: file type + 200 MB size check before upload.
2. Backend: extension whitelist (`jpg`, `jpeg`, `png`, `webp`).
3. Backend: `secure_filename()` + UUID rename — prevents path traversal and collisions.
4. Backend: PIL `Image.open()` format check — catches files with spoofed extensions; failed files are deleted.
5. `model.py`: dimension cap (8000 px/side) before Hive call — saves bandwidth and quota.

## Known Issues & Gotchas

- **Hive API is the latency floor.** 60 s timeout per request ([hive_client.py](backend/ai_model/hive_client.py)). The frontend spinner blocks the UI for the full duration — do not add work that depends on a fast response.
- **No retries** on transient Hive failures. They surface as a synthetic `"Error"` verdict with reason `"Detection service unavailable..."`.
- **`/history` swallows DB errors** and returns `[]` ([app.py:150-152](backend/app.py#L150-L152)). Don't rely on it to surface backend problems.
- **`print()` is the only logging.** No `logging` module wired up.
- **CORS is wide open** (`CORS(app)` with no args). LAN-only assumption.
- **No authentication.** Anyone on the LAN can call `/clear_history`.
- **PIL decodes entire image into RAM.** A 200 MB JPEG can spike to >1 GB resident.
- **`Test/` contains sample images only.** There is no automated test suite. `verify_hive.py` is a manual script.
- **`start.bat` is Windows-only** and parses `route print` output to find the LAN IP. There is no macOS/Linux launcher.

## When Making Changes

- **Editing routes**: update the API Surface table above if you add/remove/rename one.
- **Editing the DB schema**: there are no migrations. Bumping the schema means either a manual `ALTER TABLE` path in `init_db()` or telling the user to delete `history.db`.
- **Adding deps**: update `backend/requirements.txt`. Keep the footprint small — the v1.1 selling point is no heavy ML deps.
- **Touching `frontend/script.js`**: it is one flat file. Keep new helpers grouped by feature section (theme / network / upload / history / modals / lightbox) rather than reorganizing wholesale unless asked.
- **Touching `style.css`**: theme tokens are CSS variables defined at `:root` and `[data-theme="dark"]`. Add new colors there, not inline.
- **Hive response shape**: parsed in `ai_model/model.py`. If Hive changes their schema, that is the only place to update.

## Production Readiness

This codebase is **not production-ready**. Before any non-LAN deployment, at minimum:

- Rotate the Hive API key and confirm `.env` is gitignored.
- Restrict CORS origins.
- Add auth + HTTPS + rate limiting.
- Replace Flask dev server and `python -m http.server` with a real WSGI host (e.g. Gunicorn) behind a reverse proxy.
- Add structured logging and a retention policy for `uploads/` + `history`.

If the user asks for "production deploy" help, raise these gaps before writing infra code.
