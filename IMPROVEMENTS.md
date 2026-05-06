# TrueSight v1.0 — Improvement Plan & Task Checklist

> Comprehensive list of changes to improve code quality, fix bugs, and increase AI-vs-real detection accuracy.
> Tasks are grouped by priority. Check off items as you complete them.

---

## Tier 0 — Critical Fixes (do these first)

These change behavior the user actually sees, or fix logic bugs.

### Frontend ↔ Backend verdict mismatch
The backend computes `"AI Generated (4/5 Experts Agree)"` but the frontend ignores it and shows its own bucket label. They can disagree (e.g. backend says "AI Generated", frontend shows "Suspicious").

- [ ] In [frontend/script.js](frontend/script.js), change the result title to use `data.verdict` instead of `forensic.label`
- [ ] In [frontend/script.js](frontend/script.js) `fetchHistory()`, use `item.result` (backend verdict) instead of `forensic.label`
- [ ] Keep `getForensicLabel()` only for the **color** of the bar/title, not the text
- [ ] Add the score bucket as a small subtitle: e.g. `"AI Generated (4/5 Experts Agree) · 80% AI Likelihood"`

### Decompression-bomb risk in PIL
Dimension check runs *after* `Image.open(...).convert("RGB")`, which already loaded the image into memory.

- [ ] In [backend/ai_model/model.py](backend/ai_model/model.py), add `Image.MAX_IMAGE_PIXELS = MAX_IMAGE_DIMENSION ** 2` at module level
- [ ] Move the dimension check to use `Image.open(image_path).size` *before* calling `.convert("RGB")`
- [ ] Wrap `Image.open` in a `try/except Image.DecompressionBombError` and reject cleanly

### Failed models display as "0.0% AI Likelihood"
A model that crashed shows up as if it ran with 0% confidence — looks like a real verdict, isn't.

- [ ] In [backend/ai_model/model.py](backend/ai_model/model.py), change the `signals` dict to return `None` instead of `0` for failed models
- [ ] In [frontend/script.js](frontend/script.js) (`signals` rendering on lines ~183 and ~305), render `null`/`None` as `"unavailable"` instead of `"0.0% AI Likelihood"`
- [ ] Add a null guard: `score == null ? "unavailable" : score.toFixed(1) + "% AI Likelihood"`

### PNG/WEBP destroyed by client-side JPEG compression
[frontend/script.js:36-73](frontend/script.js) compresses every image >500 KB to JPEG-85, **including PNGs from AI tools**. Models then see a re-encoded image, losing PNG-specific artifacts and JPEG quantization signal.

- [ ] In `compressImage()`, only compress when `file.type === "image/jpeg"`
- [ ] For PNG/WEBP, send the original file untouched (16 MB cap is enough)
- [ ] When compressing JPEGs, use quality `0.95` (not `0.85`) to preserve more signal
- [ ] If file is still >16 MB after this, only then resize-and-compress as a last resort

### `extract_metadata` runs twice per upload
Once inside `predict_image` (for signals), once in `app.py` (for the response). Two redundant `Image.open()` calls.

- [ ] Make `predict_image()` return metadata as a 5th tuple element: `(label, score, reasons, signals, metadata)`
- [ ] Update [backend/app.py](backend/app.py) to use the returned metadata, remove the second `extract_metadata()` call

### Backend returns HTTP 200 even on detection error
When `predict_image` returns `("Error", 0.0, ...)`, the API still responds 200 OK.

- [ ] In [backend/app.py](backend/app.py) `/predict`, check if `label == "Error"` and return HTTP 422 with the error reason

---

## Tier 1 — High-Impact Accuracy Wins

### Add ELA (Error Level Analysis) as a 6th "expert"
Classic forensics technique. Re-save the image at JPEG-95, compute pixel-wise diff — AI images often have suspiciously uniform error patterns.

- [ ] Implement `def ela_check(pil_image) -> (is_fake, confidence, reason)` in [backend/ai_model/model.py](backend/ai_model/model.py)
- [ ] Use `numpy` (already in `requirements.txt`) for the pixel-diff math
- [ ] Add it as a vote alongside the 5 ML experts
- [ ] Bump display from "X/5" to "X/6 Experts Agree"
- [ ] Adjust verdict thresholds (currently 4/3/2 of 5; rescale for 6)

### Run all model inferences in parallel
Models are independent — running them serially wastes CPU/GPU.

- [ ] Refactor `cast_vote` calls in [backend/ai_model/model.py](backend/ai_model/model.py) to use `concurrent.futures.ThreadPoolExecutor`
- [ ] Make `cast_vote` thread-safe (replace `nonlocal` mutations with returned dicts merged after)
- [ ] Confirm 3-5× speedup on multi-core CPU

### Add C2PA / Content Credentials check
Modern cameras and Adobe products embed cryptographic provenance metadata. Strong positive "real" signal.

- [ ] Check for C2PA manifest in image (look for `Content-Credentials` XMP block, or use `c2pa-python` lib)
- [ ] If present and valid, add `votes_real += 3.0` and a reason: `"✅ Provenance Check: Verified content credentials present."`

### Resolution / aspect-ratio anomaly detection
AI tools emit specific sizes — `512×512`, `1024×1024`, `1024×1792`, `768×1344`, etc.

- [ ] In [backend/ai_model/model.py](backend/ai_model/model.py), add a list `AI_COMMON_RESOLUTIONS`
- [ ] If `(width, height) in AI_COMMON_RESOLUTIONS`, add `votes_fake += 0.5` and a soft reason
- [ ] Make sure this doesn't fire for very common camera resolutions (e.g. `1024×768` — no)

---

## Tier 2 — Code Quality & Robustness

### Promote magic numbers to named constants
[backend/ai_model/model.py](backend/ai_model/model.py) has thresholds (75, 90, 4, 3, 2, 0.25, 3.0, 25) sprinkled through code.

- [ ] Define a `CONFIG` dict at top of file with named constants
- [ ] Replace inline values: `CONF_HIGH = 90`, `CONF_MED = 75`, `WEIGHT_HIGH = 2.0`, `THRESHOLD_AI = 4`, `EXIF_FAKE_BONUS = 0.25`, `AI_SOFTWARE_BONUS = 3.0`, `JPEG_QUANT_HEAVY = 25`

### Lazy / fault-tolerant model loading
All 5 models load synchronously at import. One bad model = whole server fails to start.

- [ ] Wrap each `pipeline(...)` call in try/except in [backend/ai_model/model.py](backend/ai_model/model.py)
- [ ] If a model fails to load, log it and set the variable to `None`
- [ ] In `cast_vote`, skip models that are `None`

### Strip EXIF before storing uploads (privacy)
Original files (with GPS, etc.) are saved verbatim and served by `/uploads/<filename>`.

- [ ] After analysis completes in [backend/app.py](backend/app.py), re-save the image without EXIF: `Image.open(p).save(p, format=img.format, exif=b"")`
- [ ] Make sure this happens *after* `predict_image` (which still needs EXIF for the metadata signals)

### Remove dead code
- [ ] Drop unused `opencv-python-headless` from [backend/requirements.txt](backend/requirements.txt) (or actually use it for ELA)
- [ ] Drop unused `lastHistoryJson` polling logic in [frontend/script.js](frontend/script.js) (or implement actual polling with `setInterval`)
- [ ] In [README.txt](README.txt), fix `start_app.bat` reference to actual `start.bat`

### Better error UX in frontend
- [ ] Replace `alert("Server Error")` in [frontend/script.js](frontend/script.js) with an inline error message inside the result card, with a retry button
- [ ] Show a clear "Server unreachable" message if `fetch` rejects (vs. an HTTP error response)

### Result HTTP status semantics in `app.py`
- [ ] Magic byte rejection → HTTP 415 (`Unsupported Media Type`) instead of 400
- [ ] Dimension limit rejection → HTTP 413 (`Payload Too Large`)

### `clear_history` deletes everything in the upload folder
Currently wipes every file regardless of whether it's in the DB.

- [ ] In [backend/app.py](backend/app.py), only delete files whose `filename` appears in the `history` table
- [ ] Then `DELETE FROM history`

### Hide `/uploads/<filename>` behind a token
Anyone on the LAN can fetch any uploaded image by guessing UUIDs. Low-risk but trivial fix.

- [ ] Add `UPLOAD_TOKEN` env var, check via query string or header on `/uploads/<filename>`
- [ ] Frontend appends the token to image URLs

### Add `/health` endpoint
- [ ] Return `{"status": "ok", "models_loaded": N}` for monitoring

---

## Tier 3 — Tests & Long-Term Quality

### Add a regression test suite
The project has 17 known images in [Test/](Test/) but no automated test runs them.

- [ ] Create `backend/tests/test_predict.py`
- [ ] Label each test image as expected fake / real (or mixed)
- [ ] For each, assert `score >= 60` for fakes, `score <= 40` for reals
- [ ] Run with `pytest backend/tests/`
- [ ] Add to README

### Add a perceptual-hash cache
Identical images shouldn't run inference twice.

- [ ] Compute `imagehash.phash(pil_image)` on upload
- [ ] Add a `cache` table: `(phash TEXT PRIMARY KEY, result_json TEXT, created_at TEXT)`
- [ ] Before running models, look up the hash; if hit, return the cached result
- [ ] Add `imagehash` to [requirements.txt](backend/requirements.txt)

### Confidence calibration
Softmax outputs aren't true probabilities. Calibrate per model.

- [ ] Build a small held-out set of known-real and known-AI images
- [ ] For each model, compute its calibration curve (use `sklearn.calibration`)
- [ ] Apply temperature scaling per model
- [ ] Hardcode the temperatures into `LABEL_MAPS` or alongside it

### Bayesian model combining
Replace weighted voting with proper Bayesian combination of independent classifiers.

- [ ] Estimate each model's known accuracy from published benchmarks
- [ ] Treat each output as a likelihood ratio: `P(fake | model_says_fake) / P(fake | model_says_real)`
- [ ] Combine via Bayes' rule for posterior probability
- [ ] Compare against current weighted-voting on the regression test set

### Frequency-domain (DCT/FFT) GAN fingerprinting
Research-grade signal: GANs leave spectral peaks in the frequency domain.

- [ ] Add `scipy.fft` analysis step
- [ ] Look for known GAN fingerprints (high-frequency peaks)
- [ ] Add as a 7th expert if reliable

---

## Tier 4 — User-Facing Features

### Visual & UX improvements
- [ ] Replace text expert list with a horizontal bar chart in the modal (each expert as a colored bar)
- [ ] Add a tooltip explaining what each expert specifically detects
- [ ] Add a copy-to-clipboard button on the verdict
- [ ] Skeleton loader for the result card while analyzing (instead of just changing button text)

### Batch / comparison features
- [ ] Drag-and-drop multiple images at once → batch analyze, show grid of results
- [ ] "Compare two images" view — upload two, see verdicts side by side
- [ ] Export current scan as a PDF forensic report (with image, verdict, signals, EXIF)

### History improvements
- [ ] Search bar (by verdict text)
- [ ] Filter dropdown (AI Generated / Suspicious / Real)
- [ ] Sort by date or confidence
- [ ] Pagination (currently hardcoded to 50)
- [ ] Tag a result as "user marked: real / AI" — builds a personal ground-truth set for future calibration

### API hardening
- [ ] Add request rate limiting (e.g. `flask-limiter`)
- [ ] Restrict CORS to specific origins (currently `CORS(app)` allows all)
- [ ] Add a shared-secret token on `/predict` for LAN privacy

---

## Quick Wins (under 15 min each)

- [ ] Add `Image.MAX_IMAGE_PIXELS = 8000 ** 2` (one line, blocks decompression bombs)
- [ ] Replace `alert("Server Error")` with inline error
- [ ] Fix README's `start_app.bat` typo → `start.bat`
- [ ] Drop unused `opencv-python-headless` & `numpy` (or commit to using them)
- [ ] Make `/predict` return 422 on `"Error"` verdict
- [ ] Add `/health` endpoint

---

## Suggested Implementation Order

1. **Day 1:** Tier 0 (all 6 critical fixes)
2. **Day 2:** Tier 1 items 1, 2 (ELA expert + parallel inference)
3. **Day 3:** Tier 2 robustness + remove dead code
4. **Day 4:** Tier 3 — write the regression tests using the existing [Test/](Test/) folder
5. **Day 5+:** Tier 1 items 3, 4 (C2PA, resolution check) + Tier 4 features

---

## Files Most Affected

| File | Tier 0 | Tier 1 | Tier 2 | Tier 3 |
|------|--------|--------|--------|--------|
| [backend/ai_model/model.py](backend/ai_model/model.py) | ✓ | ✓ | ✓ | ✓ |
| [backend/app.py](backend/app.py) | ✓ |   | ✓ |   |
| [frontend/script.js](frontend/script.js) | ✓ |   | ✓ | ✓ |
| [frontend/index.html](frontend/index.html) |   |   |   | ✓ |
| [frontend/style.css](frontend/style.css) |   |   |   | ✓ |
| [backend/requirements.txt](backend/requirements.txt) |   | ✓ | ✓ | ✓ |
| [README.txt](README.txt) |   |   | ✓ |   |
| `backend/tests/` (new) |   |   |   | ✓ |

---

## Done So Far (already merged)

- [x] Fix vote-count display showing weighted sum (e.g. "10/5 Experts Agree")
- [x] Use weighted fake probability as score instead of misleading jury-certainty average
- [x] Exclude failed models from average confidence (no more 50% injection)
- [x] Add EXIF absence as weak fake signal
- [x] Add EXIF Software-tag check for known AI tool names
- [x] Add JPEG heavy-compression disclaimer
- [x] Per-model explicit label maps with keyword fallback
- [x] Replace deprecated `_getexif()` with public `getexif()`
- [x] Replace bare `except:` with logged exception handling
- [x] Magic byte validation in `app.py` (rejects renamed non-images)
- [x] Image dimension limit (8000px max per side)
- [x] `debug=False` by default (env-var opt-in only)
