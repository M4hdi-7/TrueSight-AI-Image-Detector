# TrueSight | AI Image Detector

TrueSight is a local-network web application that classifies uploaded images as **AI-generated**, **deepfake**, or **authentic**. It pairs Sightengine's GenAI + Deepfake detection API with a fallback call to Hive AI for per-engine attribution, and supplements both with on-device forensic signals (EXIF, JPEG quantization, dimension checks). All results are persisted to a local SQLite history.

The project started as a 5-model PyTorch jury in v1.0, switched to Hive AI in v1.1, and now (v1.2) runs Sightengine as the primary detector with Hive as a cost-aware fallback for generator attribution — see [`CHANGELOG.md`](CHANGELOG.md) for the full evolution.

---

## What it does

| Capability | Source | Notes |
| --- | --- | --- |
| **AI-generation score** | Sightengine `genai` model | 0–100% likelihood; drives the headline verdict |
| **Deepfake score** | Sightengine `deepfake` model | Face-swap / face-manipulation probability |
| **Generator attribution** | Hive AI (`gpt-4o`, `midjourney`, `flux`, …) | **Only called when Sightengine flags the image as AI** — saves Hive quota on real photos |
| **EXIF + camera + software** | Local PIL parsing | Flags known AI-generation software tags |
| **JPEG compression heuristic** | Local quantization table inspection | Disclaims results for heavily compressed images |
| **Verdict + forensic report** | TrueSight (this codebase) | Combines the above into a labelled verdict and bullet-pointed reasoning |
| **Scan history** | Local SQLite (`backend/history.db`) | Newest 50 scans returned by the UI |

---

## Architecture

```
                ┌──────────────┐    POST /predict (multipart)    ┌──────────────────┐
   Browser ─►   │  Flask :5000 │ ─────────────────────────────►  │  detection layer │
                └──────┬───────┘                                 │   (model.py)     │
                       │                                         └────────┬─────────┘
       UUID rename +   │                                                  │
       size/format     │                  ┌───── PIL: dims, EXIF, JPEG ◄──┤
       checks          ▼                  │                               │
                ┌──────────────┐          │                               ▼
                │  uploads/    │          │       (only if AI flagged)
                │  <uuid>.jpg  │          │           ┌────────────────────────────┐
                └──────────────┘          │           │  Hive — attribution only   │
                                          │           └────────────────────────────┘
                       │                  │                               │
                       ▼                  ▼                               │
                ┌──────────────┐    ┌──────────────────────────────┐      │
                │ history.db   │    │  Sightengine — genai+deepfake│ ◄────┘
                └──────────────┘    └──────────────────────────────┘
```

**Why this design**

- **Sightengine is primary** because its `genai` + `deepfake` models cover the two questions the user actually asks (real-or-AI and face-swap-or-not) in a single API call.
- **Hive runs only on positives.** Generator attribution (`midjourney`, `gpt-4o`, `flux`, …) is meaningful information only when the image is already judged AI. Calling Hive on real photos is wasted quota and wasted latency — so it doesn't happen.
- **EXIF and JPEG quantization** are zero-cost local signals that catch obvious cases (e.g. an EXIF `Software` tag of `"Midjourney"` is dispositive, no API call needed) and add a compression-reliability disclaimer.
- **Threshold logic is in one place** ([`backend/ai_model/model.py`](backend/ai_model/model.py) — the `LABEL_THRESHOLDS`, `AI_THRESHOLD`, `SE_STRONG`, etc. block at the top). Calibration changes don't require chasing the codebase.

---

## Repository layout

```
backend/
  app.py                       Flask routes, upload handling, SQLite I/O
  ai_model/
    model.py                   Orchestrates Sightengine + Hive cascade + local signals
    sightengine_client.py      HTTP wrapper for Sightengine's /check.json
    hive_client.py             HTTP wrapper for Hive's V3 detection API
  verify_sightengine.py        Manual smoke test for the full pipeline
  requirements.txt             Pinned dependencies (5 packages, no ML libraries)
  .env.example                 Required environment variables
frontend/
  index.html                   Single-page app shell
  script.js                    All client behaviour (no framework, no build step)
  style.css                    Light + dark theme via CSS custom properties
  manifest.json                PWA manifest
  assets/                      Icons, logos, PWA images
Test/                          Sample images for manual testing (see Test/README.md)
start.bat                      Windows launcher (auto-detects LAN IP)
CHANGELOG.md                   Version history
LICENSE                        MIT
```

---

## Setup

### 1. Install backend dependencies

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure API credentials

Copy `backend/.env.example` to `backend/.env` and fill in your keys:

```env
HIVE_API_KEY=your_hive_key
SIGHTENGINE_API_USER=your_sightengine_user
SIGHTENGINE_API_SECRET=your_sightengine_secret
```

- A **Sightengine** account is required for the primary AI/deepfake detection. Sign up at https://sightengine.com — the free tier covers 2,000 operations / 500 per day, but note that `genai` + `deepfake` together cost 10 operations per scan, so the practical limit is ~200 scans / month or 50 / day.
- A **Hive** account is only required if you want generator attribution surfaced in the UI. The cascade calls Hive *only when* Sightengine flags the image as AI, so quota burn scales with AI hit-rate, not total scans.

### 3. Smoke test (optional but recommended)

```powershell
cd backend ; venv\Scripts\python.exe verify_sightengine.py
```

Confirms credentials are valid and the pipeline returns a verdict on a known AI sample.

### 4. Evaluate the detector against `Test/`

```powershell
cd backend ; venv\Scripts\python.exe evaluate.py
```

Reads the ground-truth labels from `Test/README.md`, runs every labelled image through `predict_image`, prints a confusion matrix + precision / recall / F1, and saves a dissertation-ready Markdown report at `evaluation_report.md` plus per-image JSON at `evaluation_results.json`.

---

## Running it

From the project root:

```powershell
.\start.bat
```

This opens two windows — Flask on **port 5000** and a static file server on **port 8000** — and prints the LAN URL (e.g. `http://192.168.1.7:8000`) so other devices on the same Wi-Fi can use the UI.

Manual equivalent:

```powershell
# Window 1
cd backend ; venv\Scripts\python.exe app.py
# Window 2
cd frontend ; python -m http.server 8000
```

Set `FLASK_DEBUG=true` for Flask's autoreload + tracebacks, and `LOG_LEVEL=DEBUG` for verbose server logs.

---

## Input limits

These mirror Sightengine's published constraints so requests fail locally instead of round-tripping for an HTTP 400.

| Constraint | Value |
| --- | --- |
| Max file size | **12 MB** |
| Max dimensions | **64 megapixels** (width × height) |
| Min dimensions | **8 px** per side |
| Accepted formats | JPEG, PNG, WEBP, BMP, TIFF, JPEG 2000 |
| Animated GIF | **Not supported** — Sightengine treats animated images as video and would not return a genai score |

The Flask endpoint also enforces an extension whitelist, a `secure_filename` + UUID rename to prevent path traversal, and a PIL magic-byte check that deletes files whose declared extension doesn't match their actual format.

---

## API surface

All routes live in [`backend/app.py`](backend/app.py).

| Route | Method | Purpose |
| --- | --- | --- |
| `/predict` | POST | Analyse a multipart-uploaded image (form field `image`) |
| `/history` | GET | Return the most recent 50 scans, newest first |
| `/clear_history` | DELETE | Wipe the `history` table and the `uploads/` directory |
| `/uploads/<filename>` | GET | Serve a previously stored image |

API responses are forced `no-store`; `/uploads/*` is left cacheable since filenames are immutable UUIDs.

---

## Limitations

This is a graduation-project prototype, not a production service. Known constraints:

- **LAN-only.** CORS is wide-open and there is no auth — anyone on the same Wi-Fi can call `/clear_history`.
- **No HTTPS or rate limiting.** Flask's dev server is used directly.
- **API latency floor.** The Sightengine call is synchronous and can take several seconds; the Hive cascade adds 5–30 s on AI-positive scans.
- **Hive deepfake is not used.** Deepfake detection comes from Sightengine only.
- **Detection is not infallible.** Both providers misclassify edge cases (heavy compression, unusual aspect ratios, hand-drawn images, screenshots of AI images, etc.). Verdicts should be treated as an assistive signal, not proof.

For any non-LAN deployment, see "Production Readiness" notes in [`CLAUDE.md`](CLAUDE.md).

---

## License

MIT — see [`LICENSE`](LICENSE).
