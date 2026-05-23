# TrueSight — Architecture document

A detailed walkthrough of how TrueSight is put together. Written for the graduation-project dissertation and for any future maintainer.

---

## 1. What the project does

TrueSight is a local-network web application that classifies an uploaded image as **AI-generated**, **deepfake**, or **authentic**, and produces a forensic report explaining the verdict. It is designed to run on a single machine (the user's PC) and be reachable from other devices on the same Wi-Fi network — typically a phone for image capture and a PC for analysis.

The system is **not** an end-to-end ML model. It is an orchestrator that combines:

- A primary cloud detection API (**Sightengine**) for AI-generation and deepfake probabilities.
- A secondary cloud API (**Hive AI**) called only when the image is judged AI, to extract per-engine attribution.
- **Local forensic signals** computed on the image bytes: EXIF metadata, JPEG quantization tables, dimension checks.
- A **persistent history** in SQLite plus the original uploaded image on disk.
- A **single-page web UI** delivering verdicts, signals, and a history view.

The project's value-add is the *system around* the detection — cascade logic, local signals, validation, persistence, and presentation — not the detection itself.

---

## 2. High-level architecture

```
                       ┌───────────────────────────────────────────────┐
                       │  Browser (any device on the LAN)               │
                       │  - index.html / script.js / style.css          │
                       │  - PWA-installable                             │
                       └───────────────────┬───────────────────────────┘
                                           │  HTTP (port 8000 for static,
                                           │  port 5000 for API)
                                           ▼
                  ┌────────────────────────────────────────────────────┐
                  │  Flask backend (backend/app.py, port 5000)         │
                  │  - /predict, /history, /clear_history, /uploads/*  │
                  │  - CORS open (LAN-only assumption)                 │
                  │  - 12 MB upload cap, 64 MP image cap               │
                  └─────┬──────────────────────────┬────────────────────┘
                        │                          │
            ┌───────────▼─────────┐       ┌────────▼──────────────────┐
            │  Detection layer    │       │  Persistence              │
            │  model.py           │       │  - history.db (SQLite)    │
            │  + sightengine_*    │       │  - uploads/<uuid>.<ext>   │
            │  + hive_client.py   │       └───────────────────────────┘
            └───────────┬─────────┘
                        │
       ┌────────────────┼────────────────────────────┐
       ▼                                             ▼
┌─────────────────┐                          ┌───────────────────┐
│  Sightengine    │                          │  Hive AI          │
│  /check.json    │                          │  V3 detection API │
│  models=genai,  │  cascade (only when      │  (attribution     │
│         deepfake│   ai_score >= 50%)       │   parsing only)   │
└─────────────────┘                          └───────────────────┘
```

---

## 3. Repository layout

```
backend/
  app.py                        Flask routes, upload handling, SQLite I/O
  ai_model/
    __init__.py
    model.py                    Orchestration: validation, cascade, local signals
    sightengine_client.py       HTTP wrapper for Sightengine /check.json
    hive_client.py              HTTP wrapper for Hive V3 detection
  verify_sightengine.py         Manual smoke test for the pipeline
  evaluate.py                   Automated evaluation harness with resume
  requirements.txt              5 pinned packages
  .env.example                  Required environment variables
  history.db                    SQLite — runtime; gitignored
  uploads/                      UUID-named user images; gitignored
frontend/
  index.html                    Single-page app shell
  script.js                     All client logic, ~650 lines, no framework
  style.css                     Light + dark theme via CSS custom properties
  manifest.json                 PWA manifest
  assets/                       Icons, logos, PWA images
Test/                           Manually-curated evaluation samples (59 images)
  README.md                     Ground-truth labels and methodology
docs/
  ARCHITECTURE.md               This file
  VIVA_QUESTIONS.md             Anticipated examiner questions and answers
start.bat                       Windows launcher
README.md                       User-facing documentation
CHANGELOG.md                    Version history (v1.0 → v1.1 → v1.2)
LICENSE                         MIT
evaluation_report.md            Auto-generated Markdown report (latest run)
evaluation_results.json         Machine-readable per-image results
```

---

## 4. Request lifecycle (`POST /predict`)

When a user uploads an image, the following happens in strict order:

1. **Frontend validation** (`frontend/script.js`):
   - File type check via `file.type.startsWith("image/")` on drag-and-drop.
   - 12 MB size cap with a toast error on overflow.
   - `<input accept="image/jpeg,image/png,image/webp,image/bmp,image/tiff,image/jp2">` restricts the file picker.

2. **Backend extension whitelist** (`backend/app.py`):
   - `ALLOWED_EXTENSIONS = {jpg, jpeg, png, webp, bmp, tif, tiff, jp2}`.
   - Anything else returns `400 Unsupported file type`.

3. **Backend filename hardening** (`backend/app.py`):
   - `secure_filename()` strips path separators and non-ASCII.
   - The filename is replaced with `<uuid>.<ext>` — original name is never persisted.
   - File saved to `backend/uploads/`.

4. **Magic-byte format check** (`backend/app.py`):
   - PIL opens the saved file and inspects `img.format`.
   - If the format isn't one of `JPEG / PNG / WEBP / BMP / TIFF / JPEG2000`, the file is deleted and a 400 returned.
   - Catches renamed non-image files that passed the extension whitelist.

5. **Local image inspection** (`backend/ai_model/model.py::_read_image_signals`):
   - Width × height read from PIL.
   - EXIF parsed; camera model and Software tag extracted.
   - JPEG quantization table (luma, index 0) averaged into a single number.
   - Anything over 64 megapixels or under 8 px per side returns an Error verdict.

6. **Sightengine call** (`backend/ai_model/sightengine_client.py`):
   - Multipart POST to `/check.json` with `models=genai,deepfake`.
   - 60-second timeout. Returns parsed JSON.
   - On error (network, HTTP non-2xx, missing fields), `predict_image` returns an Error verdict with a user-readable reason.

7. **Cascade decision** (`backend/ai_model/model.py`):
   - Parse `type.ai_generated` and `type.deepfake` from the response.
   - Convert to 0–100 percentage.
   - If `ai_score >= AI_THRESHOLD (50%)`, call Hive for attribution.
   - Otherwise, skip Hive entirely — saves quota on real photos.

8. **Hive attribution call** (`backend/ai_model/hive_client.py`):
   - Multipart POST to Hive V3 endpoint with the same image.
   - Parse the `classes[]` array from `output[0]`.
   - Filter to engine-attribution classes (anything outside `{ai_generated, deepfake, not_*, none, inconclusive}`) with value > 1%.
   - Failure here is non-fatal — the verdict still completes using Sightengine's score, with a "Hive unavailable" note added.

9. **Verdict synthesis** (`backend/ai_model/model.py`):
   - Build `signals` dict: Sightengine AI Classifier, Sightengine Deepfake, and one `Attribution (<engine>)` row per Hive class above the threshold.
   - Build `reasons` list — bullet-pointed sentences explaining the verdict in plain language.
   - Map the AI score to one of five `LABEL_THRESHOLDS` buckets: AI Generated / Likely AI Generated / Suspicious / Likely Real / Real Photo.

10. **Persistence** (`backend/app.py`):
    - Insert one row into the `history` table: filename, result, confidence, reasons (JSON), timestamp.

11. **Response** (`backend/app.py`):
    - JSON body: `{verdict, score, reasons, metadata, filename, signals}`.
    - Headers force `Cache-Control: no-store`.

12. **Frontend rendering** (`frontend/script.js`):
    - Verdict card animates in, confidence bar fills, signals listed.
    - Attribution rows rendered as `🤖 AI Engine: <name>` via a regex that matches the `Attribution (...)` signal keys.
    - History tab refreshes from `GET /history` on next visit.

---

## 5. The cascade design — why it exists

The single most distinctive decision in this project is **calling Hive only when Sightengine flags an image as AI**. Three reasons:

### Cost
- Sightengine `genai + deepfake` costs **10 operations per scan**. On the 2,000-ops/month free tier, that's 200 scans/month maximum.
- Hive's quota is separate and similarly constrained.
- If both APIs were always called in parallel, every scan would burn quota in both — half of which would be wasted on real photos where attribution is meaningless.
- The cascade saves an estimated 50% of Hive calls in real-world use (assuming a roughly balanced mix of AI and real uploads).

### Latency
- Sightengine call: ~5–10 seconds.
- Hive call: ~5–30 seconds.
- Sequential cascade: 5–10 s on real photos (Sightengine only), 10–40 s on AI photos (both).
- Parallel always-on: 10–40 s on every scan. Worse user experience for the common case.

### Information value
- Per-generator attribution is **only meaningful when the image is AI**. There's no "which generator made this real photo?" question to answer.
- Calling Hive on a real photo would return engine attributions but they would be noise — Hive's output on confirmed real images contains spurious low-confidence engine matches that the frontend would have to filter out.
- The cascade trims this noise at the source.

The trade-off: AI-positive scans get an extra latency spike, and the system has a hard dependency on two providers. Both are acknowledged.

---

## 6. Detection threshold logic

Two distinct sets of thresholds, located in `backend/ai_model/model.py` for auditability.

### `AI_THRESHOLD = 50.0`

The single binary cutoff. Drives two things:
- **Cascade gate**: only `ai_score >= 50` triggers the Hive attribution call.
- **Evaluation classification**: `evaluate.py` reports precision / recall / F1 using this as the AI-or-real decision.

50% is a natural midpoint for a probability score and matches Sightengine's documented convention for treating `>0.5` as positive.

### `LABEL_THRESHOLDS = [(85, "AI Generated"), (60, "Likely AI Generated"), (45, "Suspicious / Inconclusive"), (20, "Likely Real")]`

Five-bucket UI labels. They control which verdict text the user sees, not the binary classification. They are heuristic and were chosen empirically against the bimodal score distribution observed in evaluation. They are not load-bearing for the metrics — F1 of 98.7% would be effectively unchanged if any of these were nudged ±5 points.

### `SE_STRONG = 90.0`, `SE_PARTIAL = 60.0`

Cutoffs for the *reason text* about Sightengine's confidence. Above 90% emits a ❌ "strong AI signature" bullet; 60–90% emits ⚠ "some features present"; below emits ✅ "no strong signature". Purely cosmetic — affects the explanation, not the verdict.

### `DEEPFAKE_HIGH = 90.0`, `DEEPFAKE_SUSPICIOUS = 50.0`

Same role for Sightengine's deepfake head. The 50% lower bound matches Sightengine's documented "above 0.5 is deepfake" guidance.

### `JPEG_HEAVY_COMPRESSION = 25`

Average luma quantization value above which the system flags an image as heavily compressed. Approximately corresponds to JPEG quality 50 or below. Adds a compression-reliability disclaimer to the reasons list; does not change the verdict.

---

## 7. Input validation stack

Five distinct layers, each catching a different class of bad input. Defence in depth is deliberate.

| # | Layer | Where | Catches |
| - | ----- | ----- | ------- |
| 1 | File type + 12 MB cap | Frontend (`script.js`) | Wrong-MIME drag-drops, oversized uploads before they leave the client |
| 2 | Extension whitelist | Backend (`app.py::allowed_file`) | Files arriving via curl / non-browser clients |
| 3 | `secure_filename` + UUID rename | Backend (`app.py::predict`) | Path traversal, name collisions, embedded shell metacharacters |
| 4 | PIL magic-byte check | Backend (`app.py::predict`) | Files with spoofed extensions whose actual bytes aren't a real image |
| 5 | Dimension + megapixel check | Backend (`model.py::predict_image`) | Images that would crash PIL or exceed Sightengine's 64-megapixel limit |

Each layer can fail independently and still leave the system in a safe state. Files that fail layer 4 are deleted from disk before returning.

---

## 8. Forensic local signals

These are the on-device signals TrueSight computes without calling any API.

### EXIF inspection
- Parses the standard EXIF dictionary using PIL.
- Surfaces `Camera Model` and `Software` tags.
- Adds a ❌ reason if EXIF is entirely absent ("typical of downloaded or AI images").
- Adds a ❌ reason if the `Software` tag matches a known AI-generation tool name (Midjourney, Stable Diffusion, DALL·E, Firefly, etc.).

### JPEG quantization heuristic
- For JPEG files only.
- Reads `img.quantization[0]` — the 8×8 luma quantization table.
- Averages the 64 values.
- Above 25 → "heavily compressed, result may be less reliable" disclaimer.

The compression heuristic does not improve detection — Sightengine sees the same compressed pixels. It is a **meta-signal about reliability**, qualifying the verdict for the user.

### EXIF + verdict are independent
These run regardless of what Sightengine returns. They produce reason bullets that appear alongside the API-derived signals in the forensic report.

---

## 9. Data model

Single SQLite table, created at startup:

```sql
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,         -- "<uuid>.<ext>" matching the file in uploads/
    result TEXT NOT NULL,           -- verdict label (e.g. "AI Generated")
    confidence REAL,                -- 0.0–100.0
    reasons TEXT,                   -- JSON-serialised list[str]
    timestamp TEXT                  -- "YYYY-MM-DD HH:MM"
);
```

No indexes. The history view caps at 50 rows so full-table scans are acceptable.

All queries are parameterised. The `/clear_history` endpoint truncates the table and deletes every file under `uploads/`.

---

## 10. Configuration surface

Minimal by design. Three environment variables, all loaded from `backend/.env` via `python-dotenv`:

| Variable | Required for | Notes |
| --- | --- | --- |
| `SIGHTENGINE_API_USER` | Primary detection | Sign up at sightengine.com |
| `SIGHTENGINE_API_SECRET` | Primary detection | Pair with the user above |
| `HIVE_API_KEY` | Generator attribution | Optional — system runs degraded without it |
| `FLASK_DEBUG` | Development | Defaults to off |
| `LOG_LEVEL` | Logging verbosity | Defaults to INFO |

Other constants — `MAX_FILE_SIZE`, `ALLOWED_EXTENSIONS`, `MAX_IMAGE_MEGAPIXELS`, all the detection thresholds — are hard-coded at the top of their respective files. The intent: a small number of tunable knobs, all easy to find.

---

## 11. Frontend conventions

- **No framework, no build step.** Pure HTML / CSS / JS edited directly.
- **State** lives in module-level variables in `script.js` (`currentAnalysis`, `lastHistoryJson`, drag/focus trackers). No state management library.
- **API base URL** is computed from `window.location.hostname` so a phone hitting `http://192.168.1.7:8000/` correctly addresses the backend at `http://192.168.1.7:5000/`. Critical for LAN operation.
- **Theme** is toggled via `data-theme` on `<html>` and persisted to `localStorage`. The theme script runs in `<head>` before paint to avoid a light-to-dark flash on dark-theme loads.
- **Escaping** uses `textContent` or a small `escapeHTML()` helper. `innerHTML` is never used with API-derived strings.
- **Accessibility** is load-bearing: ARIA roles for tabs and dialogs, focus traps in the details modal, `:focus-visible` styling, keyboard activation for the upload zone, and respect for `prefers-reduced-motion`.

---

## 12. Evaluation infrastructure

The `backend/evaluate.py` script is genuine project infrastructure, not a throwaway. It:

- Parses ground-truth labels out of `Test/README.md`'s markdown table (Expected column).
- Skips rows labelled `Unknown`.
- For each labelled image, calls the full `predict_image()` pipeline (Sightengine + cascade + local signals).
- Computes confusion matrix and accuracy / precision / recall / F1.
- Writes `evaluation_results.json` (machine-readable) and `evaluation_report.md` (dissertation-ready Markdown).
- **Resumes** from a previous run — successful per-image results are cached so re-running only calls the API for images that previously errored or had their ground-truth label updated. This survived a daily-quota-exhaustion event during testing.
- Auto-generates a "Failure analysis" section listing every misclassified image with the reasons emitted by the pipeline.

---

## 13. Latest evaluation summary

| Metric | Value |
| --- | --- |
| Images evaluated | 59 (40 AI, 19 real) |
| Accuracy | 98.3% |
| Precision | 100.0% |
| Recall | 97.5% |
| F1 | 98.7% |
| Misclassifications | 1 (false negative) |
| Distinct generators identified by Hive | 12 |

The single misclassification was a Reddit-sourced image whose original post explicitly identified it as a generation chosen for exceptional photorealism — an upper-bound case for what automated detection can achieve.

Full results: [evaluation_report.md](../evaluation_report.md) and [evaluation_results.json](../evaluation_results.json).

---

## 14. Known limitations

Listed in priority order. Each is acknowledged in the README and dissertation.

1. **No authentication.** Anyone on the LAN can wipe history.
2. **CORS wide open.** Same justification.
3. **No HTTPS.** Flask dev server, plain HTTP.
4. **Vendor dependency.** Sightengine outage → no detection. Mitigation: provider-agnostic orchestration in `model.py`.
5. **Free-tier quota constraints.** 500 ops/day, 2000 ops/month on Sightengine. Real evaluation usage hits this ceiling.
6. **Bimodal Sightengine output.** Most scores are 0.1% or 99.0% — almost no scores in between. Reduces threshold sensitivity but also reduces the meaningfulness of fine-grained calibration.
7. **No latency measurement.** Qualitative observations only.
8. **No baseline comparison.** "How would Sightengine-alone or Hive-alone score?" was not measured.
9. **Small test set.** 59 images. 95% confidence intervals on metrics are accordingly wide.
10. **Class imbalance.** 68% AI / 32% real. Acknowledged; reporting emphasises F1 over accuracy.
11. **No adversarial-image testing.** Out of scope.
12. **`print()` replaced with `logging`, but no centralised log aggregation.** Acceptable at this scale.
13. **Windows-only launcher.** `start.bat` parses `route print`; no macOS/Linux equivalent provided.

---

## 15. Future work

Concrete next steps, in order of value:

1. **Per-generator attribution from Sightengine directly.** Sales conversation underway; would let the project drop the Hive cascade and become provider-singular.
2. **C2PA / Content Credentials reading.** Major AI tools (Adobe Firefly, DALL·E 3, Microsoft) and cameras (Sony, Leica) now embed C2PA provenance signatures. Reading these locally is a free, high-quality forensic signal.
3. **SHA-256 dedup cache.** Repeated scans of the same image should return cached results without burning quota. ~30 lines of code.
4. **Baseline comparison evaluation.** Re-run `evaluate.py` with Sightengine-only and Hive-only modes for direct attribution to the cascade's value-add.
5. **Latency measurement.** Log per-image timing in `evaluate.py`; report mean / median.
6. **Confidence intervals.** Wilson-score CIs on all reported metrics in the evaluation report.
7. **Adversarial testing.** Curate a small set of intentionally-difficult inputs (paintings, illustrations, AI screenshots, heavily-compressed images) and measure separately.
8. **Bayesian fusion alternative.** The `hive-sighteng` branch contains an experimental implementation that fuses both providers' scores instead of cascading. Could be measured as an alternative architecture.
9. **Authentication + HTTPS.** Required for any non-LAN deployment.
10. **Production WSGI host.** Replace Flask's dev server with Gunicorn behind nginx.

---

## 16. Version history

| Version | What changed | Why |
| --- | --- | --- |
| **v1.0** | Five locally-run ML models voting on each image | Initial proof-of-concept |
| **v1.1** | Replaced jury with Hive AI V3 detection API | Local models were slow, large, and quickly outdated |
| **v1.2** | Sightengine becomes primary detector; Hive repositioned as cost-aware attribution cascade; tightened input limits to Sightengine's exact constraints; lifted thresholds into a single config block; switched to `logging`; added evaluation harness | Sightengine offers better coverage on current generators; the cascade design saves quota while preserving attribution capability |

See [CHANGELOG.md](../CHANGELOG.md) for the per-commit detail.
