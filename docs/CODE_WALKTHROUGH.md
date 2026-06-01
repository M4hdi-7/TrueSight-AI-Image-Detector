# TrueSight — Full Code Walkthrough

A deep, file-by-file, function-by-function explanation of the entire TrueSight codebase, written to prepare for the dissertation viva / supervisor discussion. The goal of this document is not to summarise the project — that's in `README.md` and `docs/ARCHITECTURE.md` — but to **leave no implementation detail unexplained**, so any question of the form *"why is this here?"* or *"what happens if X?"* has an answer below.

---

## 0. Bird's-eye view (one paragraph)

TrueSight is a Flask + vanilla-JS web app. The browser uploads an image to a Flask endpoint. Flask validates and renames the file, then hands the path to `predict_image()`. That function reads local forensic signals (size, EXIF, JPEG quantization), calls **Sightengine's** `genai + deepfake` model as the primary detector, and — **only if the image is flagged as AI** — calls **Hive AI** as a secondary lookup to identify *which* generator likely produced the image. The function returns a verdict label, a 0–100 score, a list of human-readable reasons, a signals dictionary, and an EXIF metadata summary. Flask inserts the result into a SQLite history table and returns JSON to the browser. The browser renders the verdict, a confidence bar, an attribution row (if any), an EXIF panel, and updates the history grid. There is no ML in this codebase; the intelligence lives behind two HTTP calls.

---

## 1. Repository layout (annotated)

```
TrueSight_v1.0_copy/
├── backend/
│   ├── app.py                      Flask app — routes, DB, file I/O, validation
│   ├── ai_model/
│   │   ├── __init__.py             Empty — marks ai_model as a package
│   │   ├── model.py                Orchestrator: thresholds, cascade, reason-building
│   │   ├── sightengine_client.py   HTTP wrapper for Sightengine /check.json
│   │   └── hive_client.py          HTTP wrapper for Hive's V3 detection API
│   ├── verify_sightengine.py       Manual smoke test (NOT a pytest suite)
│   ├── evaluate.py                 Ground-truth evaluation harness → confusion matrix + report
│   ├── requirements.txt            5 pinned packages, zero ML deps
│   ├── history.db                  SQLite DB (created at first run)
│   ├── uploads/                    UUID-named saved images
│   └── .env                        HIVE_API_KEY, SIGHTENGINE_API_USER/SECRET (gitignored)
├── frontend/
│   ├── index.html                  Single-page shell, two tabs + two modals + lightbox
│   ├── script.js                   ~650 lines, flat, no framework
│   ├── style.css                   ~1400 lines, CSS-variable theming (light + dark)
│   ├── manifest.json               PWA manifest
│   └── assets/                     Logos, favicons, PWA icons
├── Test/                           Sample images + Test/README.md ground-truth table
├── start.bat                       Windows launcher (auto-detects LAN IP)
├── evaluation_report.md            Output of `evaluate.py` — confusion matrix + per-image table
├── evaluation_results.json         Machine-readable evaluation cache
├── README.md                       User-facing docs
├── CHANGELOG.md                    v1.0 → v1.1 → v1.2 evolution
├── CLAUDE.md                       AI-pair-programming guardrails
└── docs/
    ├── ARCHITECTURE.md             High-level architecture write-up
    ├── VIVA_QUESTIONS.md           Pre-prepared viva Q&A
    └── dissertation/               Full dissertation chapters + appendices
```

---

## 2. The end-to-end request flow (numbered, with file:line anchors)

The user uploads one image and gets one verdict. Here is every step in order.

1. **Browser file pick.** [frontend/script.js:258-278](../frontend/script.js#L258-L278) listens to the `<input type="file">` `change` event. It checks the file is ≤ 12 MB (matching the backend cap exactly), reads the file as a base64 data URL via `FileReader`, displays the preview, hides the drop-zone, and enables the "Analyze Image" button.
2. **Click "Analyze".** [frontend/script.js:304-404](../frontend/script.js#L304-L404) builds a `FormData` with field name `image` and `fetch`es `POST /predict`.
3. **Flask receives the request.** [backend/app.py:72-131](../backend/app.py#L72-L131) is the `/predict` handler:
   - Rejects empty filename or wrong extension (whitelist: jpg/jpeg/png/webp/bmp/tif/tiff/jp2).
   - `secure_filename()` sanitises any user-supplied name (defence-in-depth).
   - Renames the file to `<uuid4-hex>.<ext>` → prevents collisions and path-disclosure.
   - Saves to `backend/uploads/`.
   - Opens with PIL once to verify the magic bytes (`img.format` must be one of `JPEG / PNG / WEBP / BMP / TIFF / JPEG2000`). If it isn't, the file is deleted and a 400 returned. This is the "renamed `.exe` to `.jpg`" defence.
4. **Hand off to detection layer.** [backend/app.py:105](../backend/app.py#L105) calls `predict_image(image_path)` from `ai_model.model`.
5. **`predict_image()` reads local signals.** [backend/ai_model/model.py:62-85, 128](../backend/ai_model/model.py#L62-L85) opens the image once and pulls `(width, height, metadata{has_exif, camera, software}, quant_avg)`. This single PIL open is intentional — opening the image multiple times would double the memory pressure of large JPEGs.
6. **Dimension checks.** [model.py:135-158](../backend/ai_model/model.py#L135-L158) rejects images > 64 MP total or < 8 px per side. These mirror Sightengine's published limits — fail locally instead of round-tripping for an HTTP 400.
7. **Sightengine call.** [model.py:160-186](../backend/ai_model/model.py#L160-L186) calls `sightengine_client.classify_image(path)`. On network exception or non-success status, returns an `"Error"` verdict with a user-facing reason — the UI keeps working.
8. **Score parsing.** [model.py:188-191](../backend/ai_model/model.py#L188-L191) reads `response["type"]["ai_generated"]` and `response["type"]["deepfake"]` (both in 0.0–1.0) and multiplies by 100.
9. **Cascade decision.** [model.py:193-196](../backend/ai_model/model.py#L193-L196): if `ai_score >= 50%` (the `AI_THRESHOLD` constant), call `_hive_attributions(path)` to fetch per-generator probabilities. Otherwise skip Hive entirely — saves quota and 5–30 s of latency on real photos.
10. **Hive attribution parsing.** [model.py:88-110](../backend/ai_model/model.py#L88-L110) iterates `response["output"][0]["classes"]` and keeps only items whose class name is **not** one of the 9 "base" classes (`ai_generated`, `deepfake`, `inconclusive`, etc.). Everything left is treated as a candidate engine attribution (`midjourney`, `gpt-4o`, `flux`, …). Probabilities < 1 % are dropped as noise.
11. **Signals dictionary built.** [model.py:202-210](../backend/ai_model/model.py#L202-L210) populates `signals` with Sightengine's two scores plus one `Attribution (<engine>)` entry per Hive-returned engine.
12. **Reasons list built.** [model.py:212-248](../backend/ai_model/model.py#L212-L248) appends 4–6 human-readable bullet strings with emoji prefixes (✅ ⚠️ ❌ 🤖):
    - Sightengine AI verdict tier (strong / partial / none).
    - Top Hive engine (only if AI-flagged).
    - Deepfake tier (only if score is present and ≥ 50 %).
    - EXIF presence and camera model.
    - AI-software EXIF flag (matches against `AI_SOFTWARE_NAMES`).
    - JPEG quantization warning if `quant_avg > 25`.
13. **Verdict label selection.** [model.py:251-255](../backend/ai_model/model.py#L251-L255) walks `LABEL_THRESHOLDS` (a descending list of cut-offs) and picks the first label whose cut-off the score crosses. Defaults to `"Real Photo"`.
14. **Return tuple.** `(label, ai_score, reasons, signals, metadata)` flows back to Flask.
15. **DB insert + JSON response.** [app.py:108-127](../backend/app.py#L108-L127) writes one row to `history` and returns `{verdict, score, reasons, metadata, filename, signals}`. `score` is divided by 100 here so the frontend gets a fraction; the frontend multiplies by 100 back to a percentage (deliberate mirror of the wire format).
16. **Frontend render.** [script.js:328-394](../frontend/script.js#L328-L394) maps the score onto its own 5-tier label/colour (independent of the backend's label — see § 6.2), updates the headline, progress bar, signals list, attribution row, and stores `currentAnalysis` for the details modal.
17. **History refresh.** [script.js:394](../frontend/script.js#L394) fires `fetchHistory()` so the History tab's grid is up-to-date when the user switches tabs.

End-to-end, one scan involves: 1 multipart upload (browser → Flask), 1 disk write, 1 PIL open, 1 Sightengine API call, 0 or 1 Hive API call, 1 SQLite insert, 1 JSON response, ~6 DOM updates.

---

## 3. `backend/app.py` — Flask layer

### 3.1 Imports and config (lines 1-33)

- `from dotenv import load_dotenv; load_dotenv()` runs **before** any `os.environ` read. If this came after, the `HIVE_API_KEY` and Sightengine credentials would be missing.
- `logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper(), ...)` configures the root logger; v1.2 retired the old `print()` calls in favour of this.
- `BASE_DIR = os.path.dirname(os.path.abspath(__file__))` makes all paths absolute and relative-to-this-file, so the app behaves identically regardless of `cwd`.
- `ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "bmp", "tif", "tiff", "jp2"}` matches `MIME` whitelist on the `<input accept="">` and on the magic-byte check.
- `MAX_FILE_SIZE = 12 * 1024 * 1024` matches Sightengine's hard upload limit. Putting this on `app.config["MAX_CONTENT_LENGTH"]` means Flask returns HTTP 413 for any oversized request automatically — saves us writing manual size checks on the server.
- `CORS(app)` is unrestricted. Reasoning: this is a LAN-only app; any tightening should happen with the deployment, not in code. See § 9 on production gaps.

### 3.2 `init_db()` (lines 39-56)

```sql
CREATE TABLE IF NOT EXISTS history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    filename    TEXT NOT NULL,        -- the on-disk uuid name, not original
    result      TEXT NOT NULL,        -- verdict label string ("AI Generated", ...)
    confidence  REAL,                 -- ai_score 0–100
    reasons     TEXT,                 -- JSON-serialised list[str]
    timestamp   TEXT                  -- "YYYY-MM-DD HH:MM" local time
)
```

- `IF NOT EXISTS` makes startup idempotent.
- `reasons` is a JSON string — SQLite has no array type, and v1.x did not justify adding a normalised `reasons` table.
- `timestamp` is stored as ISO-like text, not a numeric epoch. Trade-off: easier to read in `.db` browsers, less precise. We never sort on it (we sort on `id DESC`), so the lossy format is fine.
- The schema has **no indexes**. Justified: the only read query is `ORDER BY id DESC LIMIT 50`, which uses the implicit `rowid` index.

If you want to **migrate** the schema (e.g. add a `deepfake_score` column), there is no Alembic / Flask-Migrate; you either ship an `ALTER TABLE` in `init_db()` or tell the user to delete `history.db`. v1.2 chose neither and just kept the schema stable.

### 3.3 `allowed_file()` (lines 58-60)

A two-line extension whitelist. Note the `rsplit(".", 1)` — files named `evil.png.exe` will see `"exe"` here and be rejected. The `secure_filename()` call later still sanitises the rest.

### 3.4 `serve_image()` (lines 66-68)

A thin wrapper over Flask's `send_from_directory`. `send_from_directory` is **safe against path traversal** by design — it refuses any filename containing `..` or absolute paths. So requesting `/uploads/../app.py` returns 404, not the source code.

### 3.5 `predict()` — the main endpoint (lines 72-131)

The validation order is deliberate:

1. **Presence check** — `if "image" not in request.files` returns 400 immediately. No file written.
2. **Empty filename** — covers the case where the form was submitted with no selection.
3. **Extension whitelist** — rejected before any disk write.
4. **`secure_filename()` + UUID rename** — sanitises and decouples the on-disk name from anything the user gave us. The original filename is discarded entirely; we never log it, never display it.
5. **File saved.** ✱ At this point, an attacker has succeeded in writing arbitrary bytes to `uploads/<uuid>.<our-chosen-ext>`. The next check is what stops them from doing anything useful with that.
6. **PIL magic-byte check.** `Image.open()` will throw on any file that isn't a real image, even if the extension says it is. If `img.format` is something unexpected (e.g. an animated GIF that PIL might still open), we explicitly remove the file from disk before returning 400. This is the layer that makes the renamed-`.exe` attack moot.

Three more details about this handler:

- The **whole function is wrapped in `try/except`** that returns a generic `"Internal server error"` 500 with the real exception logged at `logger.exception` level. Never leak stack traces to the client.
- The DB `INSERT` uses `sqlite3.connect(...)` with `with` — auto-commits on success, auto-closes the connection on any exception. We never hold a connection open between requests.
- The response body is hand-shaped, not auto-serialised from the tuple. The frontend depends on the exact field names (`verdict`, `score`, `reasons`, `metadata`, `filename`, `signals`). Any rename here is a breaking API change.

### 3.6 `get_history()` (lines 135-159)

- `conn.row_factory = sqlite3.Row` lets us index columns by name (`row["filename"]`) instead of position. Tiny ergonomic win; safe because `sqlite3.Row` is a fixed shape.
- The 50-row cap is hardcoded — no pagination. The UI is one scrolling grid, not paged.
- `json.loads(row["reasons"])` deserialises the bullet list. If the JSON is malformed (it shouldn't be — only we write it), this would raise and trigger the outer `except`, which returns `[]` to the client. That swallows the error silently. **Known gotcha** (called out in `CLAUDE.md`): the History tab will look empty if reads start failing for any reason, not just an empty DB.

### 3.7 `clear_history()` (lines 163-180)

Deletes everything in `uploads/` then runs `DELETE FROM history`. Two consequences:

- **Race condition**: if a new scan is in-flight while `clear_history` runs, the new image might be deleted before its DB row is written. Acceptable on a single-user LAN app.
- **No auth**. Anyone on the LAN can wipe history with `curl -X DELETE`. The frontend gates this behind a confirm modal ([script.js:457-474](../frontend/script.js#L457-L474)), but that's UX, not security.

### 3.8 `add_header()` — cache headers (lines 184-191)

- API responses get `Cache-Control: no-store, no-cache, must-revalidate`. Browsers must re-fetch every time. This avoids the History tab showing a stale list after a new scan or a `clear_history`.
- `/uploads/*` is exempt — those files are immutable UUID-named blobs, so we let them cache. This is critical for the History grid: 50 thumbnails would re-download on every tab switch otherwise.

### 3.9 `app.run()` (lines 193-195)

`host='0.0.0.0'` is what makes the backend reachable from other LAN devices (phones). `127.0.0.1` would bind to loopback only. `FLASK_DEBUG=true` enables the dev autoreloader + interactive tracebacks — **never** for production (RCE risk via the Werkzeug debugger).

---

## 4. `backend/ai_model/model.py` — the orchestrator

This is the single most important file in the project. Everything that distinguishes TrueSight from "a thin wrapper around the Sightengine API" lives here: thresholds, the cascade, the EXIF/JPEG signals, and the verdict/label mapping.

### 4.1 Module-level constants (lines 14-49)

All knobs live at the top of the file so calibration doesn't require chasing the code:

| Constant | Value | Meaning |
|---|---|---|
| `MAX_IMAGE_MEGAPIXELS` | 64 | Sightengine's own upper bound. |
| `MIN_IMAGE_DIMENSION` | 8 px | Sightengine refuses tiny images. |
| `AI_THRESHOLD` | 50.0 | At/above this, we call Hive for attribution and mark the image as AI in the evaluation harness. |
| `LABEL_THRESHOLDS` | list of `(cutoff, label)` | Drives the headline verdict string. 5 tiers. |
| `DEFAULT_LABEL` | `"Real Photo"` | Returned when score falls below the lowest threshold. |
| `SE_STRONG` / `SE_PARTIAL` | 90 / 60 | Cut-offs for the "Sightengine Detector" reason line wording. |
| `DEEPFAKE_HIGH` / `DEEPFAKE_SUSPICIOUS` | 90 / 50 | Cut-offs for the "Deepfake Check" reason line. |
| `JPEG_HEAVY_COMPRESSION` | 25 | Average luma quantization above which we add a "result less reliable" disclaimer. |
| `AI_SOFTWARE_NAMES` | 13 entries | Substring match against the EXIF `Software` tag. |
| `_HIVE_BASE_CLASSES` | 9 entries | The set of Hive class names that are verdict-level, not engine-level. Anything outside this set is treated as a candidate engine. |

**Why two threshold layers?** `AI_THRESHOLD` is the binary cut-off used by the cascade (call Hive yes/no) and by the evaluation harness. `LABEL_THRESHOLDS` is a finer-grained 5-tier mapping used only for the headline verdict shown to the user. Keeping them separate means you can tune the user-facing language without changing the cascade logic.

**Why a substring match on `AI_SOFTWARE_NAMES`?** EXIF `Software` strings in the wild look like `"Adobe Firefly 2.0"`, `"Stable Diffusion XL"`, `"ComfyUI custom workflow"` — exact matching would miss almost everything. A substring match is permissive on purpose. The list contains both `"dall-e"` and `"dall·e"` because the middle character can be ASCII hyphen or Unicode middle-dot depending on the generator.

### 4.2 `_read_image_signals(image_path)` (lines 62-85)

Opens the image **once** with PIL, in a `with` block, and pulls four things:

- `width, height` — for the megapixel check.
- `img_format` — used only to gate the quantization check (only JPEGs have quant tables).
- `exif_data = img.getexif()` — PIL's modern EXIF API. `exif_data.items()` yields `(tag_id, value)`; we map `tag_id` to its name via `TAGS` from `PIL.ExifTags`.
- `quant_avg` — average value of the luma (channel 0) quantization table. Computed only for JPEGs that actually have a quantization attribute set.

**Why average the luma table?** JPEG stores per-frequency quantization steps in an 8×8 matrix. Higher values mean coarser quantization (more compression, more information loss). The mean is a crude but stable scalar proxy for "how heavily was this re-encoded". It's not exposed in the UI; it's used only to add the "may be less reliable" reason line.

**EXIF defensiveness.** Some EXIF values come back as non-strings (`PIL.TiffImagePlugin.IFDRational`, bytes, etc.). We always `str(...)` them before storing, so the JSON serialiser later can't crash on something exotic.

The function returns `(width, height, metadata, quant_avg)` where `metadata` is always a dict with the keys `has_exif`, `camera`, `software` — never `None`, never missing keys. This matters because the frontend grid in the details modal reads `item.metadata?.camera || "N/A"`; if the backend returned `None`, the frontend would render `"None"`.

### 4.3 `_hive_attributions(image_path)` (lines 88-110)

Calls `hive_classify(path)` inside a `try/except` and returns `{}` on any failure. Hive is positioned as a **best-effort enrichment**, not a hard dependency — if Hive is down, the user still gets a Sightengine-based verdict, just without the engine attribution row.

After the call, it walks `response["output"][0]["classes"]` and keeps:

- Items whose class name is **not** in `_HIVE_BASE_CLASSES` (skips Hive's own verdict classes like `ai_generated`, `deepfake`, `inconclusive`).
- Items whose probability is **> 0.01** (drops noise).

The return type is `dict[engine_name, percentage]`, e.g. `{"midjourney": 87.4, "flux": 6.1}`.

### 4.4 `predict_image()` — the main function (lines 113-257)

This is the function the rest of the system orchestrates around. The control flow:

1. **Read signals.** `_read_image_signals(path)`. On exception (e.g. PIL can't open the file even though the upload check passed) — return `"Error"` with reason "Could not read image file". Defensive; in practice, this should be unreachable because `app.py` already did a PIL open. But the function is reachable independently from `evaluate.py` and `verify_sightengine.py`, so the check is here too.
2. **Dimension gates.** Return `"Error"` if MP > 64 or any side < 8 px.
3. **Sightengine call.** Three failure modes are handled independently:
   - Network/HTTP exception → `"Detection service unavailable..."`
   - HTTP 200 but `status != "success"` → bubble Sightengine's error message.
   - Missing `type.ai_generated` field → `"Invalid response format"`.
4. **Score extraction.** `ai_score = float(ai_generated_raw) * 100`. `deepfake_score` is `None` if absent — we never assume it's there.
5. **Cascade gate.** `image_is_ai = ai_score >= AI_THRESHOLD`. Only when `True` do we call `_hive_attributions(path)`. The top engine is `max()` over the dict.
6. **Build `signals` dict.** Keys: `"Sightengine AI Classifier"`, `"Sightengine Deepfake"` (if present), and one `"Attribution (<engine>)"` per Hive engine. **The exact key prefix `"Attribution ("` matters** — the frontend uses a regex to split signals into "stats" and "attribution" rows. Renaming this key without updating [script.js:359-371](../frontend/script.js#L359-L371) would silently break the UI rendering.
7. **Build `reasons` list.** Six independent reason-emitting blocks, each guarded by a threshold. Each reason is a short emoji-prefixed string. The emoji prefix (`✅` / `⚠️` / `❌`) is what the frontend uses in `classifySignal()` ([script.js:481-487](../frontend/script.js#L481-L487)) to pick the badge colour, so the emoji is part of the contract.
8. **Headline label.** Loop over `LABEL_THRESHOLDS` (already in descending order). First match wins.
9. **Return.** `(label, round(ai_score, 2), reasons, signals, metadata)`.

**Why is the verdict label produced server-side when the frontend also has its own label function?** Two reasons:

- The headline label is stored in `history.db` for the user's records, independent of frontend versions.
- The frontend `getForensicLabel()` ([script.js:29-41](../frontend/script.js#L29-L41)) uses **different cut-offs** (20 / 45 / 60 / 85) and **different labels** (`Real Photo`, `Likely Real`, `Hard to Tell`, `Suspicious`, `AI Generated`) than the backend. This is *deliberate* — the backend label is for long-term storage and "how does the report read", the frontend label is for "what colour and icon do we show right now". They're allowed to diverge.

---

## 5. `backend/ai_model/sightengine_client.py` — Sightengine HTTP wrapper

Twenty-six lines. Single responsibility: send the image to `https://api.sightengine.com/1.0/check.json` with the `genai,deepfake` models requested, and return the parsed JSON. Notes:

- **Credentials come from `os.environ`**, not module-level globals. So if the user updates `.env` and rerun the Flask process, the new keys are picked up.
- A missing key raises `RuntimeError` with an actionable message ("check your .env file") — caught one frame up in `model.py`, which converts it into a verdict-level error reason.
- `requests.post(..., files={"media": f}, timeout=60)`. The `files` parameter forces multipart/form-data, which is what Sightengine expects. The 60-second timeout is the **synchronous latency ceiling**; the entire UI blocks for at most this long.
- `response.raise_for_status()` converts HTTP 4xx/5xx into `requests.HTTPError`, which `model.py` catches as a generic exception.

**Quota cost.** Each scan invokes both models, which Sightengine bills as **10 operations** (per their pricing — 5 ops per model). The free tier is 2,000 ops / month, so ~200 scans is the practical ceiling on the free plan.

---

## 6. `backend/ai_model/hive_client.py` — Hive HTTP wrapper

Even smaller — 35 lines. Posts to `https://api.thehive.ai/api/v3/hive/ai-generated-and-deepfake-content-detection` with `Authorization: Bearer <HIVE_API_KEY>` and a multipart `media` field. Same 60 s timeout, same `raise_for_status()`.

**The Hive V3 response shape** (relevant portion):

```json
{
  "output": [
    {
      "classes": [
        {"class": "ai_generated", "value": 0.98},
        {"class": "midjourney",   "value": 0.87},
        {"class": "flux",         "value": 0.06},
        {"class": "deepfake",     "value": 0.01}
      ]
    }
  ]
}
```

The model layer's job is to (a) ignore the verdict classes and keep the engine classes, (b) convert `value` to a percentage, (c) drop noise below 1 %.

**Why Hive at all, given Sightengine is primary?** Sightengine's `genai` model returns *whether* the image is AI-generated, not *which* model produced it. Hive's V3 explicitly returns per-engine probabilities. Combining the two costs more, so the cascade only pays the Hive cost when there's a positive Sightengine score to attribute.

---

## 7. `backend/verify_sightengine.py` — manual smoke test

Not a pytest suite. A 73-line script that:

1. **Test 1.** Pops the Sightengine env vars and runs `predict_image()` on a sample image — confirms the function returns `"Error"` gracefully rather than crashing.
2. **Test 2.** Restores the env vars, runs `predict_image()` on a known-AI sample (`Midjourney-for-Beginners-AI-Art-by-Sprinkle-of-AI-4-XL-683x1024.jpg`), and prints the result.

`_safe_print(reasons)` strips non-ASCII (the emoji prefixes) so Windows `cmd` doesn't choke on the encoding.

This script is run **manually** — there is no CI, no automated test gate, no coverage report. The project's deliberate scope decision was: this is a graduation prototype, not a production system; the value is in the orchestration design and the dissertation, not in test infrastructure.

---

## 8. `backend/evaluate.py` — evaluation harness

This is the file that produces the numbers your dissertation cites. Walkthrough:

### 8.1 Ground-truth source

`Test/README.md` contains a markdown table. The relevant rows look like:

```
| `IMG_8923.jpg`               | Real    | ... |
| `midjourney-portrait-v6.jpg` | AI      | ... |
| `someimage.jpg`              | Unknown | ... |
```

`parse_ground_truth()` (lines 67-85) walks the file with a regex (`_TABLE_ROW`), keeps rows whose **Expected** column starts with `"Real"` or `"AI"` (case-insensitive), and skips `"Unknown"` / blank ones. Result: `{filename: "real"|"ai"}`.

This means **you control which images are in the metrics by editing one markdown table**. You don't have to move files, rename them, or change code.

### 8.2 Single-image evaluation (`evaluate_one`, lines 95-141)

For each labelled file:

1. Verify the file exists on disk (the markdown can drift from the filesystem).
2. Call `predict_image(path)`.
3. Convert the model's `ai_score` into a binary `predicted_label` using the same `AI_THRESHOLD = 50` constant imported from `model.py`. **Single source of truth** — if you bump the threshold to 60, both the runtime and the evaluation use it without further edits.
4. Walk the `signals` dict and pull the highest-scoring `Attribution (<engine>)` entry as `top_engine`.
5. Wrap everything in a `Result` dataclass with a `correct` boolean.

### 8.3 Caching to avoid re-spending API budget (lines 277-309)

`load_cached_results()` reads `evaluation_results.json` from a previous run. Any **successful** result whose ground-truth label still matches the current `Test/README.md` is reused — no second API call. Errored results are **not** cached, so transient Hive/Sightengine failures get retried automatically next run. This is what lets you iterate on the markdown table and reasons logic without burning quota.

### 8.4 Confusion matrix and metrics (lines 148-165)

The positive class is **AI**. So:

- **TP** = true AI, predicted AI.
- **FP** = true real, predicted AI. (The "I called my holiday photo a deepfake" failure mode — most user-facing pain.)
- **FN** = true AI, predicted real. (The detector missed an AI image.)
- **TN** = true real, predicted real.

From these: accuracy, precision, recall, F1 — standard binary classification formulas.

### 8.5 Outputs

- **stdout**: a sorted per-image table + the matrix + the four metrics. Sort key: `(true_label != "ai", -ai_score)` — AI images first, descending by score, so the most confident calls are at the top.
- **`evaluation_results.json`**: machine-readable, with a `summary` block and a `results` list. This is also the file the cache reads from on the next run.
- **`evaluation_report.md`**: dissertation-ready Markdown with methodology, sample composition, confusion matrix, metrics, per-image breakdown, **failure analysis** (each wrong call is its own subsection with the model's reasons), and an errors section. This is the artefact you cite verbatim in chapter 7.

---

## 9. `frontend/index.html` — DOM shell

Two views (tabs) + three overlays + a toast container, all in a single 233-line file.

### 9.1 `<head>`

- Three `Cache-Control` `<meta>` tags + `Pragma` + `Expires` to defeat browser caching of `index.html` itself (we ship `style.css?v=7` and `script.js?v=7` with cache-busting query strings — bumping `v=` is the manual cache-bust knob during development).
- Three favicon links + an Apple-touch-icon for installability.
- The PWA `manifest.json` is linked here.
- The Apple-specific `apple-mobile-web-app-*` metas make the iOS "Add to Home Screen" experience look like a native app (status bar style, standalone display).
- `theme-color: #003057` (TrueSight navy) controls the chrome of the address bar on Android.
- An **inline theme bootstrap script** runs before stylesheet parsing:

  ```js
  const t = localStorage.getItem('theme') || 'light';
  document.documentElement.setAttribute('data-theme', t);
  ```

  This avoids a flash-of-unstyled-content where the page renders in light mode for one frame before the JS sets the dark attribute. The variable is `t`, the attribute is on `<html>`, which means every CSS rule under `[data-theme="dark"]` applies before paint.

### 9.2 Structure

- `<header>` holds two logo images (`logo-light` and `logo-dark`), CSS hides whichever one doesn't match the current theme.
- `<nav class="tab-bar">` has two `<button role="tab">`s and a theme toggle pill. ARIA attributes are full-fat: `aria-selected`, `aria-controls`, `tabindex` swaps between `0` and `-1` so keyboard users only land on the active tab.
- `#home-view` is a two-column layout — the intro card on the left and the upload card on the right. CSS collapses to a single column on narrow screens.
- `#dropZone` is a `role="button" tabindex="0"` div (so it's keyboard-focusable). The hidden `<input type="file">` lives inside it and is `.click()`-ed programmatically.
- `#previewContainer` and `#result` are hidden by default and unhidden by JS.
- `#detailsModal`, `#confirmModal`, and `#imageLightbox` are three sibling overlays at the end of `<body>`. All three are `role="dialog" aria-modal="true" aria-hidden="true"` and use focus traps when open.
- `#toastContainer` is the live region (`role="status" aria-live="polite"`) where transient messages append.

**Why role="button" on a div** instead of a `<label for="">`? Because we wanted the dropzone to be both clickable and droppable, and to look like a card. A `<label>` could not be a drop target nor host the hover/focus styling we wanted. The div + `role=button` + `keydown` handler for Enter/Space matches WAI-ARIA's button pattern.

---

## 10. `frontend/script.js` — all the behaviour

Flat file, ~650 lines, grouped by section. There is no module system, no bundler, no transpilation. Everything is `<script src="script.js">`. Function ordering is top-to-bottom by feature area:

### 10.1 Theme toggle (lines 1-9)

`toggleTheme()` flips the `data-theme` attribute and persists to `localStorage`. The matching CSS variable block in `style.css` does the rest.

### 10.2 Network setup (lines 11-18)

```js
const currentIP = window.location.hostname;
const BASE_URL  = `http://${currentIP}:5000`;
```

This is the line that **makes the phone-from-LAN flow work**. If we hardcoded `localhost`, only the PC running both servers could use the app. By taking the hostname from `window.location`, a phone at `http://192.168.1.7:8000/index.html` will derive `BASE_URL = http://192.168.1.7:5000`.

### 10.3 `getForensicLabel(score)` (lines 29-41)

Five tiers, returning `{label, icon, color, score}`. Used for:

- The headline result title.
- The history card title and progress accents.

The cut-offs (20 / 45 / 60 / 85) are **different from the backend's `LABEL_THRESHOLDS`** — see § 4.4 for why. Colours are hardcoded hex (matches the `--success` / `--danger` palette from CSS but bypasses the variable system because they're inlined into `style="color:..."`).

### 10.4 Toast + confirm helpers (lines 55-131)

- `showToast(message, type, duration)` builds a DOM node, appends it to `#toastContainer`, schedules a CSS-animated removal at `duration` ms (default 3.5 s). Clicking the toast dismisses early.
- `showConfirm({...})` returns a **Promise**. The dialog blocks until the user clicks Accept or Cancel (or presses Escape, or clicks the overlay). Three things happen on open:
  1. The previous `document.activeElement` is saved.
  2. The modal is shown and focus is placed on the **Cancel** button (safer default).
  3. `keydown` is intercepted: `Escape` cancels, `Tab` triggers `trapFocus()`.

  On close, all listeners are removed and focus is restored to the saved element. This is full WCAG modal behaviour.

### 10.5 `trapFocus(e, container)` (lines 133-147)

Standard focus-trap pattern: collects all focusable children, wraps Tab from last → first and Shift+Tab from first → last.

### 10.6 `escapeHTML(s)` (lines 149-156)

Replaces `& < > " '`. Used everywhere a Hive engine name or EXIF software string gets injected into `innerHTML`. **This is the only XSS defence on the frontend** — anything reading user-controlled or API-controlled text into `innerHTML` must go through this helper.

Where we use `innerHTML` deliberately: the signals breakdown ([script.js:373-378](../frontend/script.js#L373-L378)) and history grid items ([script.js:440-446](../frontend/script.js#L440-L446)). Where we use `textContent`: reason bullets in the modal ([script.js:507-509](../frontend/script.js#L507-L509)). Mixing styles like this is intentional — `textContent` is the safer default; `innerHTML` is used only where we want emoji prefixes / icons / structured layout.

### 10.7 `switchTab(tabName)` (lines 161-180)

Updates `aria-selected`, `tabindex`, the `.active` class on buttons; toggles `display: none/block` and the `hidden` attribute on each view. Side effect: switching to `history` triggers `fetchHistory()`.

### 10.8 DOMContentLoaded handler (lines 185-405)

The single big handler that wires up the home view. In order:

- **Click → file picker.** `dropZone.click()` → `fileInput.click()`.
- **Keyboard support.** Enter or Space on the dropzone triggers the picker.
- **Drag and drop.** Four listeners (`dragenter`, `dragover`, `dragleave`, `drop`) maintain a `dragCounter` to handle child-element bounce. `dragenter` fires multiple times when dragging over nested elements, so we increment/decrement and only remove the visual highlight when the counter hits 0. On drop, the file is hand-transferred into `fileInput.files` via `DataTransfer` so the existing `change` handler runs.
- **Global drag prevention.** A second pair of listeners on `window` prevents the browser from navigating to the dropped file if the user misses the dropzone (default browser behaviour is to open the image in the tab).
- **File change.** Size check (12 MB hard cap, matches backend), `FileReader.readAsDataURL` for preview, hide dropzone, show preview, enable Analyse button.
- **`resetForNewAnalysis()`.** Single function that returns the UI to its initial state. Called by the Remove button and the Analyse-Another button. Includes a `scrollIntoView` and `focus` so the user lands cleanly on the dropzone for the next scan.
- **Upload button click.** Constructs `FormData`, `fetch`es `/predict`, on success:
  - Maps score → forensic label.
  - Writes the headline title with the label's icon and colour.
  - Writes "X% AI Likelihood" into `#confValue`.
  - Sets the progress bar's width and colour.
  - Hides the loader.
  - Builds the signals breakdown (`statsHtml` for stats, `attributionHtml` for `Attribution (...)` entries — the **prefix split** is the same one Hive's response shape produced upstream).
  - Saves the result to `currentAnalysis` (used when the user clicks "View Detection Details").
  - Calls `fetchHistory()` so the History tab is fresh.

  On HTTP error: pulls `data.error` if present, shows it in a toast, restores the button.

  On network exception: shows a generic "Server error" toast.

### 10.9 `fetchHistory()` (lines 410-455)

- **Change detection.** Stores the last JSON string in `lastHistoryJson`. If the new response is identical, we **don't re-render** — saves a flicker and 50 DOM rebuilds when the user spam-clicks the refresh button.
- **Empty state.** Shows a "No history yet." message.
- **Error state.** Shows "Connection failed. Check that the backend is running." — the most common diagnostic case.
- **Rendering.** For each item, builds a card with a thumbnail (served by `/uploads/<filename>`), a forensic label headline, and a confidence line. Clicking the card opens the details modal pre-filled with that item's data.

### 10.10 `clearHistory()` (lines 457-474)

Promise-awaits the confirm dialog, then `DELETE /clear_history`, then refreshes. Shows a success toast on completion.

### 10.11 Modal + lightbox (lines 479-647)

- `openDetailsModal(data)` accepts an explicit item (from history) or falls back to `currentAnalysis`. Populates the image, EXIF labels, reasons list, and signals list (the signals are appended as additional reasons inside the same `<ul>`, each with a colour class derived from the score: red ≥ 60, amber ≥ 30, green < 30).
- `classifySignal(text)` is a string-match dispatcher: it looks at the emoji prefix (`✅` / `❌` / `⚠️`) and assigns a CSS class. This is why the backend's emoji prefixes are part of the API contract.
- The **lightbox** is a second overlay (`#imageLightbox`) layered on top of the details modal. The trick handled in `closeLightbox()` is that closing the lightbox should **not** release the body's `modal-open` class if the details modal is still open underneath. It checks both other modals' display state before deciding.

---

## 11. `frontend/style.css` — theming and layout

1,393 lines. The big design decisions:

### 11.1 CSS-variable theme tokens

All colours, radii, and shadows live in `:root` ([style.css:1-35](../frontend/style.css#L1-L35)) and `[data-theme="dark"]` ([style.css:37-57](../frontend/style.css#L37-L57)). Every rule that uses colour does so via `var(--name)`. Adding a new component does **not** require adding a new colour decision; you reach for an existing token.

### 11.2 Light + dark in one stylesheet

The dark variant is `[data-theme="dark"]` overrides at the top, plus a few `[data-theme="dark"] .something` rules later for components where the override isn't a colour swap (e.g. logos: light/dark variants of the PNG are toggled with `display: none/block`).

### 11.3 Accessibility-load-bearing features

- `:focus-visible` styling everywhere — keyboard users see clear focus rings, mouse users don't get a focus ring on click.
- The theme toggle pill has an explicit `focus-visible` style on `.pill-track` so its keyboard focus state is visible.
- `@media (prefers-reduced-motion: reduce)` clauses (not shown above but present further down the file) flatten transitions for motion-sensitive users.
- Modal overlay padding + `body.modal-open { overflow: hidden }` to prevent background scroll behind dialogs.

### 11.4 Layout strategy

- The `body` is a flex container that centres a `.app-container { max-width: 460px }`. The whole app looks like a mobile column even on a 4K monitor — intentional, since the primary device is a phone.
- The home view uses `.home-grid` (CSS grid) to put the intro panel beside the upload card on wide screens and stack them on narrow.
- The history view is a CSS grid of cards (`.history-grid`).

---

## 12. `frontend/manifest.json` — PWA

Five-key manifest: `name`, `short_name`, `description`, `start_url`, `scope`, `display: standalone`, plus 192 px and 512 px maskable icons. This is what makes "Add to Home Screen" produce an icon that opens the app full-screen (no browser chrome). The orientation is locked to portrait — again, phone-first.

---

## 13. `start.bat` — Windows launcher

32 lines. Does three things:

1. Parses `route print` output to extract the LAN IPv4 (the IP whose default-route entry's destination is `0.0.0.0`).
2. Opens a new `cmd` window for the backend (`venv\Scripts\python.exe app.py`).
3. Opens a second `cmd` window for the static file server (`python -m http.server 8000`).
4. Prints `http://<IP>:8000` for the user to type into their phone.

**Caveats** (already in `CLAUDE.md`): Windows-only, depends on `route print`'s output format, no graceful shutdown — closing the windows kills the processes hard. There is no `start.sh` equivalent.

---

## 14. Security model — every check, in order

When the question comes up in viva — "how do you defend against malicious uploads?" — here's the full ordered list:

1. **Browser-side accept filter** ([index.html:105](../frontend/index.html#L105)) — `accept="image/jpeg,image/png,..."`. UX only; can be bypassed by any non-browser client.
2. **Browser-side size check** ([script.js:262](../frontend/script.js#L262)) — `file.size > 12 MB → reject`. Same caveat as above.
3. **Flask `MAX_CONTENT_LENGTH`** ([app.py:33](../backend/app.py#L33)) — HTTP 413 returned by Flask before our handler runs. Cannot be bypassed.
4. **Extension whitelist** ([app.py:83](../backend/app.py#L83), [app.py:58-60](../backend/app.py#L58-L60)) — only the 8 whitelisted extensions are accepted.
5. **`secure_filename()`** ([app.py:88](../backend/app.py#L88)) — strips path separators, control chars, leading dots. Defence-in-depth.
6. **UUID rename** ([app.py:90](../backend/app.py#L90)) — original filename is discarded entirely. No user-controlled bytes end up in any path.
7. **PIL magic-byte check** ([app.py:97-102](../backend/app.py#L97-L102)) — `Image.open()` parses the actual bytes; if the format isn't one we expect, the file is deleted from disk and a 400 is returned. This is the layer that closes the "renamed .exe as .jpg" attack.
8. **Dimension cap** ([model.py:135-158](../backend/ai_model/model.py#L135-L158)) — > 64 MP is rejected to bound memory + reject things Sightengine would reject anyway.
9. **Parameterised SQL** ([app.py:113-116](../backend/app.py#L113-L116), [app.py:142](../backend/app.py#L142)) — all SQLite queries use `?` placeholders. SQL injection isn't possible against the schema as written.
10. **HTML escaping on the frontend** — `escapeHTML()` is applied to every Hive/EXIF/Sightengine string that lands in `innerHTML`.
11. **Cache-Control on API responses** — prevents proxies/browsers from serving stale verdicts.

What we **deliberately don't** defend against:

- **CSRF.** No auth → nothing to forge.
- **Auth bypass.** No auth in the first place — LAN-only assumption.
- **Network-level attacks.** No HTTPS — LAN-only.
- **Rate limiting / DoS.** Single user → not a concern for the design point.

These are the gaps you'd close before any non-LAN deployment.

---

## 15. Data flow types (the wire contract)

The shape of the `/predict` JSON response — frontend and backend agree on these exact keys:

```ts
{
  verdict:  string                  // "AI Generated" | "Likely AI Generated" | ... | "Real Photo" | "Error"
  score:    number                  // 0.0–1.0 (fraction; frontend multiplies by 100)
  reasons:  string[]                // each starts with ✅ / ⚠️ / ❌ / 🤖 (used as a tag by the frontend)
  metadata: {
    has_exif: boolean,
    camera:   string,               // "Unknown" if absent
    software: string,               // "Unknown" if absent
  },
  filename: string,                 // the UUID name, used to fetch /uploads/<filename>
  signals:  {
    "Sightengine AI Classifier":   number,           // %
    "Sightengine Deepfake"?:       number,           // % (absent if Sightengine returned nothing)
    "Attribution (<engine>)"?:     number            // % (zero or more)
  }
}
```

And the `/history` response:

```ts
Array<{
  id:         number,
  filename:   string,
  result:     string,        // verdict label
  confidence: number,        // 0–100
  reasons:    string[],
  timestamp:  string         // "YYYY-MM-DD HH:MM"
}>
```

Both responses are sent with `Cache-Control: no-store`.

---

## 16. Performance characteristics

For viva discussion, here is the breakdown of *where time goes* on a single scan:

| Phase | Typical time | Notes |
|---|---|---|
| Browser → Flask upload | < 100 ms on LAN | Bound by Wi-Fi throughput; one 10 MB image at 100 Mbps ≈ 0.8 s. |
| File save + PIL magic check | 50–200 ms | Bound by disk write + PIL header parse. Larger JPEGs are slower because PIL has to read more bytes to confirm the format. |
| `_read_image_signals` | 100–500 ms | Dominated by EXIF read; quantization read is constant. |
| Sightengine call | **1–5 s** | The dominant cost. Cloud round-trip + their inference. |
| Hive call (when AI-flagged) | **5–30 s** | Only on positives. Hive's V3 is slower than Sightengine. |
| DB insert | < 10 ms | One row, one parameterised statement. |
| Network response + DOM update | < 100 ms | Tiny JSON payload. |

**Total**: 1.5–6 s for a real photo (no Hive), 6–35 s for an AI photo (cascade triggered). The frontend spinner deliberately gives no progress percentage because both Sightengine and Hive give no streaming hint — only a final response.

**Memory** is dominated by PIL decoding the JPEG. A 12 MB JPEG can decode to > 500 MB in RAM. Multiple concurrent uploads on the Flask dev server could OOM the machine; this is one of the production-readiness items.

---

## 17. Why the project is the way it is — design decisions you can defend

1. **Why Flask?** Smallest viable Python web framework, no learning curve for the supervisor / external reviewer, no build step. The whole backend fits in one file you can read in five minutes.
2. **Why vanilla JS, no framework?** Same reasoning. The frontend is < 700 lines of script; React or Vue would add 100 KB of runtime, a build step, and a learning surface, in exchange for code organisation we don't yet need.
3. **Why two cloud APIs instead of one?** Sightengine + Hive together cover *both* questions the user asks: "is it AI?" *and* "which generator?". Neither provider answers both well alone (at least not on the plans we use). The cascade keeps Hive cost proportional to AI hit-rate.
4. **Why SQLite, not Postgres / Mongo?** Zero-config, file-based, no separate process to manage. The data set is bounded at ~50 visible rows. Postgres would be deployment overhead with zero functional benefit.
5. **Why no auth?** Out of scope for a LAN-only graduation prototype. Adding it without HTTPS would be cargo-cult security.
6. **Why two thresholds (`AI_THRESHOLD` and `LABEL_THRESHOLDS`)?** One for cascade and evaluation (binary), one for headline display (5-tier). Decoupling them means UI copy changes don't shift the evaluation metrics.
7. **Why is the evaluation harness in a separate file with caching?** Because Sightengine + Hive cost real money. Caching successful results across runs means you can iterate on the report format, the reasons logic, and the markdown table without spending budget. Failed runs are intentionally not cached so transient outages get retried.
8. **Why drag-and-drop with a `role="button"` div instead of a `<label>`?** A `<label>` cannot be a drop target. The div + ARIA + keyboard-handler pattern is the WAI-ARIA-recommended way to make a custom button accessible.
9. **Why two label functions (backend + frontend)?** The backend label is *durable* (stored in `history.db`, present in API responses, used by `evaluate.py`). The frontend label is *transient* (just for colour/icon in the current view). Letting them diverge means visual tuning never touches storage.
10. **Why emoji prefixes in reasons?** Because they double as a machine-readable tag (`classifySignal()` reads the prefix to pick a colour class) **and** a human-readable cue. Two birds, one byte.

---

## 18. Known limitations (be upfront in the viva)

From `README.md` and our own audit:

- **No HTTPS, no auth, no rate limits.** LAN-only by design.
- **CORS wide open** (`CORS(app)` no args). Same reasoning.
- **PIL memory.** 12 MB JPEG → potentially 500 MB+ resident.
- **No retries** on transient Sightengine / Hive failures. Surfaces as a generic `"Detection service unavailable"` reason.
- **`/history` swallows DB errors** and returns `[]`. So an empty grid might mean empty DB or might mean DB read failed.
- **No structured logging** of API costs. We can count rows in `history.db` to estimate, but we don't track per-API cost explicitly.
- **No automated tests.** `verify_sightengine.py` is manual, `evaluate.py` is a black-box harness. No unit tests on `model.py`'s reason-building logic.
- **No pagination on history.** Capped at 50.
- **Detection is not infallible.** Both providers misclassify edge cases: heavy compression, unusual aspect ratios, hand-drawn images, screenshots of AI images, etc. The 5-tier "Likely Real" / "Hard to Tell" / "Suspicious" language is deliberately hedged for this reason.
- **`start.bat` is Windows-only** and depends on `route print` output format. No macOS / Linux launcher.

---

## 19. What changed across versions (for the "how did the project evolve" question)

From `CHANGELOG.md`:

- **v1.0** — Five locally-run PyTorch / transformers / ONNX models, jury-voting. Heavy install footprint, slow CPU inference, large weight files. Justified the "thin orchestrator over cloud APIs" pivot by demonstrating the cost of self-hosted ML.
- **v1.1** — Removed the entire ML stack. Switched to Hive V3 as the sole detector. Added the per-engine attribution rows, the dark mode pass, the PWA manifest, the accessibility pass, the SQLite history, the `/clear_history` endpoint.
- **v1.2 (current)** — Sightengine became primary because its `genai + deepfake` covers both questions in a single call. Hive demoted to **attribution-only** fallback, called only when Sightengine flags AI. Input limits aligned to Sightengine's. Thresholds consolidated to one block at the top of `model.py`. `print()` replaced with `logging`. Frontend asset paths consolidated under `assets/`. Dependencies pinned.

The trajectory you can defend: each version reduced infrastructure complexity and improved cost-awareness, while increasing the verdict's reliability by combining better-suited providers.

---

## 20. Likely viva questions, mapped to where the answer lives

| Question | Section of this doc / file |
|---|---|
| Walk me through what happens when I click "Analyze". | § 2 |
| How do you stop someone uploading an `.exe` renamed to `.jpg`? | § 14, step 7 |
| Why two cloud APIs? Why not just one? | § 17.3, § 6 last paragraph |
| What does the cascade save you? | § 4.1 "Why two threshold layers", § 16 |
| Where would you put auth if you had to ship this publicly? | § 9 ("Production Readiness" in `CLAUDE.md`) |
| How do you measure accuracy? | § 8, plus `evaluation_report.md` |
| Why is the verdict-label logic in two places (server + client)? | § 4.4 last paragraph, § 17.9 |
| What happens if Hive is down? | § 4.3 ("best-effort enrichment") |
| What's the biggest single bottleneck? | § 16 — the Sightengine call is the latency floor. |
| How would you scale this to 1,000 users? | Not currently a goal — but: gunicorn + reverse proxy, Postgres, S3-backed uploads, auth, background worker for the API call so the UI doesn't block. Each is a feature, not a refactor. |
| Why no tests? | § 7 last paragraph (scope decision, dissertation prototype). |
| What does the SQLite schema look like and why? | § 3.2 |
| How does the phone reach the PC's backend? | § 10.2 (the `window.location.hostname` trick) + `start.bat` (LAN IP). |
| Is the system accessible? | § 11.3 + § 9.2 — full ARIA + focus-visible + reduced-motion + keyboard parity. |
| How big is the dependency footprint? | 5 packages, no ML libs. `backend/requirements.txt`. |
| If Sightengine changed their response schema, where would you fix it? | `backend/ai_model/model.py`, the score-extraction block at lines 177-191. Sightengine's wire format is touched in exactly one place. |

---

End of walkthrough. If you want to read the code in the order it executes, follow § 2 with the file tabs open. If you want to read it by responsibility, the order is `app.py` → `model.py` → `sightengine_client.py` → `hive_client.py` → `script.js` → `index.html` → `style.css`.
