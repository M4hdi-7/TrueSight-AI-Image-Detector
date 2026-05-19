# TrueSight — Hive AI Migration Handoff

> **For the next agent picking up this work.** You have not seen the prior conversation. This document is self-contained — read it top to bottom before touching code.

---

## 1. What TrueSight Is

TrueSight is a local web app that classifies an uploaded image as **Real** or **AI-Generated**. The user is a university student (Mahdi Alzoubi, Yarmouk University) building this as a final project — supervised by Dr. Rafat Alshorman. The project is already at v1.0 and was documented in [PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md). **Read that file first** for the full architecture overview.

**Stack:** Python 3 + Flask backend, vanilla HTML/CSS/JS frontend, SQLite for history. Runs locally on `0.0.0.0:5000` so a phone on the same Wi-Fi can use it.

**Repo layout:**
```
TrueSight_v1.0/
├── backend/
│   ├── app.py              # Flask routes, DB, validation (DO NOT need to rewrite)
│   ├── ai_model/
│   │   └── model.py        # ⚠️ THIS is the file getting replaced
│   ├── history.db
│   ├── uploads/
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── script.js           # ⚠️ small UI update needed (signals panel)
│   ├── style.css
│   └── logo.png, etc.
├── start.bat
├── PROJECT_DOCUMENTATION.md
└── HIVE_MIGRATION_HANDOFF.md (this file)
```

---

## 2. The Shift: Why We're Migrating

**Current implementation (v1.0):** A "5-model jury" of Hugging Face image classifiers running locally through `torch` + `transformers`. Each model votes, votes are weighted by confidence, EXIF metadata adds bonus signals, and a tiered label is produced. See §4 of [PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md) for the full algorithm.

**Why it's being replaced:**
- Loading 5 transformer models requires ~GB of RAM and slow cold-start
- Detection quality is hit-or-miss across image types
- The user wants to use a single, dedicated commercial detection API: **Hive AI's AI-Generated Content Classification endpoint**

**New approach (v1.1):** One HTTP call to Hive's API per image. Hive returns probability scores for AI-generated vs. human-generated content (and often sub-classes like which model generated it). We use those scores to produce the same `(label, score, reasons, signals)` tuple the rest of the app already expects.

### Decision already made
We are doing a **clean replacement**, not a pluggable backend. The jury system is being dropped entirely. The `v1.0-jury` git tag preserves the old version for the academic record.

---

## 3. The Critical Contract You Must Preserve

The whole reason this migration is a clean swap is that **the function signature in `model.py` is the only thing `app.py` knows about**. Keep this signature identical and the backend route changes become zero:

```python
def predict_image(image_path: str) -> tuple[str, float, list[str], dict]:
    """
    Returns:
        label:      str   — headline verdict ("AI Generated", "Likely Real", etc.)
        score:      float — 0.0–100.0 representing AI likelihood %
        reasons:    list  — human-readable bullet points for the forensic report
        signals:    dict  — per-signal breakdown for the UI (was per-expert in v1.0)
    """
```

```python
def extract_metadata(image_path: str) -> dict:
    """
    Returns: {"has_exif": bool, "camera": str, "software": str}
    """
```

`app.py` calls both functions at [app.py:93-94](backend/app.py#L93-L94). Do **NOT** change `app.py` unless you also have a reason to evolve the JSON response.

---

## 4. The User's Workflow Preferences

Before you start, internalize these (the user said them explicitly):

- **Work on the `feature/hive-api-integration` branch.** Never commit Hive work directly to `main`. The user already created it and tagged `main` as `v1.0-jury`.
- **Small commits, in this order** (the user agreed to this plan):
  1. `feat: add Hive API client module`
  2. `feat: wire Hive into predict_image, remove jury`
  3. `chore: drop torch/transformers, add requests + dotenv`
  4. `feat: update frontend signals panel for Hive response shape`
  5. `docs: rewrite section 4 for Hive backend`
- **Never hardcode the API key.** Use `.env` + `python-dotenv`. Add `.env` to `.gitignore`. Provide a `.env.example` with `HIVE_API_KEY=your_key_here`.
- **Don't introduce abstractions you don't need.** No factory pattern, no detector base class — there is exactly one backend now.
- **No emojis in code or commits** unless the user asks. The current `reasons` strings *do* use ✅/❌/⚠️ in their text — those are user-facing report content, not decoration; preserve that style for the new reasons.
- **Defer to the user before destructive actions** (dropping the venv, deleting `history.db`, etc.).

---

## 5. What You Need to Build

### 5.1 New Hive API client

Recommended layout — create `backend/ai_model/hive_client.py`:

```python
import os
import requests

HIVE_API_URL = "https://api.thehive.ai/api/v2/task/sync"  # confirm the exact endpoint with Hive docs
HIVE_API_KEY = os.environ.get("HIVE_API_KEY")
TIMEOUT_SECONDS = 30

def classify_image(image_path: str) -> dict:
    """POSTs the image to Hive, returns the parsed JSON response."""
    if not HIVE_API_KEY:
        raise RuntimeError("HIVE_API_KEY not set — check .env")
    with open(image_path, "rb") as f:
        response = requests.post(
            HIVE_API_URL,
            headers={"Authorization": f"Token {HIVE_API_KEY}"},
            files={"image": f},
            timeout=TIMEOUT_SECONDS,
        )
    response.raise_for_status()
    return response.json()
```

> ⚠️ **The exact endpoint URL, auth header format, and request shape depend on which Hive product the user is paying for.** Confirm with their docs (https://docs.thehive.ai) — the snippet above is a likely-shape skeleton, not a verified call. Ask the user for the curl example they tested with, if they have one.

### 5.2 New `predict_image` in `model.py`

Replace the entire file body. Keep only:
- The two function signatures (`predict_image`, `extract_metadata`)
- The EXIF logic (`extract_metadata` is unchanged — it doesn't depend on the jury at all)
- The `AI_SOFTWARE_NAMES` constant — Hive may not detect every metadata trick, so we still want the bonus

Skeleton:

```python
from PIL import Image
from PIL.ExifTags import TAGS
from .hive_client import classify_image

AI_SOFTWARE_NAMES = [
    "stable diffusion", "dall-e", "dall·e", "midjourney", "adobe firefly",
    "firefly", "imagen", "comfyui", "automatic1111", "novelai", "invokeai",
    "generative", "ai-generated",
]
MAX_IMAGE_DIMENSION = 8000  # keep — protects against malicious huge images


def predict_image(image_path):
    pil_image = Image.open(image_path).convert("RGB")
    w, h = pil_image.size
    if w > MAX_IMAGE_DIMENSION or h > MAX_IMAGE_DIMENSION:
        return ("Error", 0.0,
                [f"Image too large ({w}x{h}px). Max {MAX_IMAGE_DIMENSION}px."], {})

    try:
        hive_response = classify_image(image_path)
    except Exception as e:
        print(f"Hive API error: {e}")
        return "Error", 0.0, ["Detection service unavailable."], {}

    # 🔑 Parse the Hive response — exact field paths depend on Hive's response shape.
    # Typical pattern: response.status[0].response.output[0].classes is a list of
    # {"class": "ai_generated", "score": 0.97} entries. Confirm with the actual JSON.
    ai_score, sub_scores = parse_hive_response(hive_response)  # YOU WRITE THIS

    reasons = []
    signals = sub_scores  # dict like {"ai_generated": 97.0, "not_ai_generated": 3.0, ...}

    # Build human-readable reasons from the Hive scores
    if ai_score >= 90:
        reasons.append("❌ Hive Detector: Strong AI generation signature detected.")
    elif ai_score >= 60:
        reasons.append("⚠️ Hive Detector: Some AI-generation features present.")
    else:
        reasons.append("✅ Hive Detector: No strong AI-generation signature.")

    # EXIF supplement — still useful even with Hive
    meta = extract_metadata(image_path)
    if not meta["has_exif"]:
        ai_score = min(100.0, ai_score + 5)  # small nudge
        reasons.append("❌ Metadata Check: No camera data found.")
    software_val = meta.get("software", "Unknown").lower()
    if software_val not in ("unknown", "") and any(kw in software_val for kw in AI_SOFTWARE_NAMES):
        ai_score = max(ai_score, 95.0)  # near-certain — bump verdict
        reasons.append(f"❌ Metadata Check: Software tag reads '{meta['software']}'.")

    # Tiered label — same thresholds as before for UI consistency
    if ai_score >= 85:
        label = "AI Generated"
    elif ai_score >= 60:
        label = "Likely AI Generated"
    elif ai_score >= 45:
        label = "Suspicious / Inconclusive"
    elif ai_score >= 20:
        label = "Likely Real"
    else:
        label = "Real Photo"

    return label, round(ai_score, 2), reasons, signals


def extract_metadata(image_path):
    # UNCHANGED from v1.0 — copy verbatim from current model.py:184-202
    ...
```

> The `parse_hive_response()` helper is the one piece you absolutely must verify against a real Hive response. Print the raw JSON the first time and shape the parser from what you see.

### 5.3 Frontend signals panel update

The current UI at [script.js:244-260](frontend/script.js#L244-L260) renders:
```js
for (const [expert, score] of Object.entries(s)) {
    statsHtml += `<p>${expert}: ${score.toFixed(1)}% AI Likelihood</p>`;
}
```

This is **already generic** — it iterates whatever keys come back. As long as `signals` is a flat `{string: number}` dict (e.g. `{"AI Generated": 97.0, "Human": 3.0}`), the existing UI will work without changes. **Verify this before assuming the frontend needs editing.**

The modal at [script.js:367-374](frontend/script.js#L367-L374) does the same — iterates the dict. Should also Just Work.

So step 4 of the commit plan might end up being a no-op or just a label-text tweak — that's fine.

### 5.4 `requirements.txt`

Current dependencies likely include `torch`, `transformers`, `Pillow`, `flask`, `flask-cors`. After migration:
- **Remove:** `torch`, `transformers` (no more local models)
- **Keep:** `flask`, `flask-cors`, `Pillow`, `werkzeug`
- **Add:** `requests`, `python-dotenv`

The user will need to rebuild their venv after this change. **Warn them before suggesting `pip install -r requirements.txt`** — they may want to create a fresh venv rather than uninstalling torch.

### 5.5 `.env` and `.gitignore`

- Create `backend/.env` (NOT committed): `HIVE_API_KEY=...`
- Create `backend/.env.example` (committed): `HIVE_API_KEY=your_hive_api_key_here`
- Ensure `.gitignore` includes `.env`, `*.env` (check first — don't blindly append if already present)
- Add `from dotenv import load_dotenv; load_dotenv()` at the top of `app.py` so the key is loaded before `model.py` imports

---

## 6. The Database Schema

**No changes needed.** The `history` table ([app.py:32-41](backend/app.py#L32-L41)) stores `result TEXT, confidence REAL, reasons TEXT (JSON)`. All three still apply with Hive output. Don't drop or recreate `history.db` — the user may have demo data in it.

---

## 7. Testing Checklist

Before the user calls the migration done:
- [ ] Real photo (e.g. `Test/SEI_217242335.webp`) → "Likely Real" or "Real Photo"
- [ ] AI image with `Software=Midjourney` EXIF tag → bumped to ≥95%, "AI Generated"
- [ ] AI image with no EXIF → reasonable AI score
- [ ] Image > 8000px on a side → returns the size-error tuple, doesn't crash
- [ ] No `HIVE_API_KEY` env var → graceful error message in the UI, not a 500
- [ ] Hive returns an error / times out → graceful error message, doesn't crash the app
- [ ] History view still loads previous v1.0 scans (their `reasons` strings are old format but should still render)
- [ ] `DELETE /clear_history` still wipes uploads + DB rows

---

## 8. Gotchas & Things Not to Touch

- **`app.py` validation chain** (extension whitelist, magic-byte check, UUID rename, 16 MB cap) — keep all of it. It's not jury-related and is correct.
- **`app.py` after_request cache-busting headers** — keep them, they help during development.
- **The `history.db` file** — don't delete it. If the schema ever needs a column, add via `ALTER TABLE`, don't drop.
- **`PROJECT_DOCUMENTATION.md`** — the user uses this for their viva/discussion with the doctor. §4 (the jury section) needs to be rewritten for Hive after the code change is verified. Don't rewrite the rest — overview, FR mapping, DB section, frontend section are all still accurate.
- **The `Test/` folder** — sample images for manual QA. Don't move or rename.
- **`start.bat`** — boots the backend. Likely doesn't need changes unless you alter the venv path.

---

## 9. Open Questions to Ask the User If You Hit Them

1. Which exact Hive product are they using? (`AI-Generated Content Classification` is one of several — auth & response shape differ)
2. Do they have a working `curl` example from Hive's docs they've already tested? (Saves you guessing the request format)
3. Do they want to keep the EXIF metadata bonus signals, or trust Hive's score alone? (Recommendation: keep — costs nothing, catches obvious cases)
4. Are they OK with the migration being live-only (no offline fallback)? (Hive being down = TrueSight being down)

---

## 10. When You're Done

- All commits on `feature/hive-api-integration`
- Tested against the checklist in §7
- §4 of [PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md) rewritten for Hive
- This handoff file (`HIVE_MIGRATION_HANDOFF.md`) can be deleted in the merge commit — it's a transient artifact
- Recommend the user merge with `git merge --no-ff feature/hive-api-integration` to keep a visible "switched to Hive" boundary in `git log`
- **Do not push or merge yourself** — let the user do that explicitly
