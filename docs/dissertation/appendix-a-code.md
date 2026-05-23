# Appendix A: Code

This appendix contains the complete source code of TrueSight's backend, presented in narrative order from the Flask entry point inward. Each file is preceded by a short prose description of its role and the call relationships it participates in.

The frontend code (`frontend/index.html`, `frontend/script.js`, `frontend/style.css`) is not included inline to keep this appendix to a reasonable length. It is published in full in the project's public GitHub repository at the URL in Appendix C.

---

## A.1 `backend/app.py` — Flask backend

The HTTP entry point. Owns the Flask application, all four routes (`/predict`, `/history`, `/clear_history`, `/uploads/<filename>`), and the SQLite schema. Performs the first layers of input validation (presence, extension, magic-byte), persists each scan to the database, and serves uploaded images back to the frontend. Delegates all detection logic to `ai_model/model.py::predict_image`.

```python
import os
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

import uuid
import sqlite3
import json
import logging
import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from PIL import Image
from ai_model.model import predict_image
from werkzeug.utils import secure_filename

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("truesight")


# --- SETTINGS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
DB_FILE = os.path.join(BASE_DIR, "history.db")
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "bmp", "tif", "tiff", "jp2"}
MAX_FILE_SIZE = 12 * 1024 * 1024  # 12 MB — Sightengine's hard upload limit

app = Flask(__name__)
CORS(app) # Allow the frontend (phone) to talk to the backend (PC)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE # <--- SAFETY CAP

# Make sure the upload folder exists so we don't get errors
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- DATABASE SETUP ---
def init_db():
    """Creates the history file if it doesn't exist yet."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                result TEXT NOT NULL,
                confidence REAL,
                reasons TEXT,
                timestamp TEXT
            )
        ''')
        conn.commit()

# Run the DB setup immediately when the app starts
init_db()

def allowed_file(filename):
    """Checks if the user uploaded a valid image format."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# --- SERVER ROUTES ---

# 1. Image Server
@app.route('/uploads/<filename>')
def serve_image(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# 2. The Main Brain (Predict)
@app.route("/predict", methods=["POST"])
def predict():
    try:
        # Basic validation checks
        if "image" not in request.files:
            return jsonify({"error": "No image uploaded"}), 400

        file = request.files["image"]
        if file.filename == "":
            return jsonify({"error": "Empty filename"}), 400

        if not allowed_file(file.filename):
            allowed_list = ", ".join(sorted(ALLOWED_EXTENSIONS)).upper()
            return jsonify({"error": f"Unsupported file type. Accepted: {allowed_list}."}), 400

        # Give the file a unique name so we don't overwrite old photos
        original_name = secure_filename(file.filename)
        ext = original_name.rsplit(".", 1)[1].lower() if "." in original_name else "jpg"
        filename = f"{uuid.uuid4().hex}.{ext}"
        image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(image_path)

        # Verify actual file content matches the declared extension (magic byte check).
        try:
            with Image.open(image_path) as img:
                if img.format not in {"JPEG", "PNG", "WEBP", "BMP", "TIFF", "JPEG2000"}:
                    raise ValueError(f"Unexpected format: {img.format}")
        except Exception:
            os.remove(image_path)
            return jsonify({"error": "File is not a valid image."}), 400

        # --- CALL DETECTION PIPELINE + COMPOSE FORENSIC REPORT ---
        label, confidence, reasons, signals, metadata = predict_image(image_path)

        # Save everything to our history file
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        reasons_json = json.dumps(reasons)

        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO history (filename, result, confidence, reasons, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (filename, label, confidence, reasons_json, timestamp))
            conn.commit()

        return jsonify({
            "verdict": label,
            "score": confidence / 100.0,
            "reasons": reasons,
            "metadata": metadata,
            "filename": filename,
            "signals": signals
        })

    except Exception as e:
        logger.exception("Unhandled error in /predict: %s", e)
        return jsonify({"error": "Internal server error"}), 500

# 3. Get History
@app.route("/history", methods=["GET"])
def get_history():
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM history ORDER BY id DESC LIMIT 50")
            rows = cursor.fetchall()

            history_data = []
            for row in rows:
                history_data.append({
                    "id": row["id"],
                    "filename": row["filename"],
                    "result": row["result"],
                    "confidence": row["confidence"],
                    "reasons": json.loads(row["reasons"]),
                    "timestamp": row["timestamp"]
                })

            return jsonify(history_data)
    except Exception as e:
        logger.error("Failed to read /history: %s", e)
        return jsonify([])

# 4. Wipe Everything
@app.route("/clear_history", methods=["DELETE"])
def clear_history():
    try:
        # Delete the actual image files
        for f in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, f)
            if os.path.isfile(file_path):
                os.remove(file_path)

        # Wipe the database rows
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM history")
            conn.commit()

        return jsonify({"status": "cleared"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Prevent the browser from caching API responses so the UI always shows fresh data.
# Uploaded images live under /uploads/<uuid>.<ext> and are immutable — let them cache.
@app.after_request
def add_header(response):
    if request.path.startswith('/uploads/'):
        return response
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

if __name__ == "__main__":
    # Host 0.0.0.0 is crucial so other devices on Wi-Fi can see the server
    app.run(host='0.0.0.0', port=5000, debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true")
```

---

## A.2 `backend/ai_model/model.py` — Detection orchestration

The heart of the detection pipeline. Reads local image signals (EXIF, JPEG quantization), enforces dimension limits, calls the Sightengine client unconditionally, and conditionally calls the Hive client when the image is judged AI. Composes the final verdict label, confidence score, bullet-point reasons list, signals dictionary, and EXIF metadata summary that the frontend renders. Every detection threshold and limit is defined as a named constant at the top of the file for auditability.

```python
import logging

from PIL import Image
from PIL.ExifTags import TAGS

from .sightengine_client import classify_image as sightengine_classify
from .hive_client import classify_image as hive_classify

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Input limits (mirror Sightengine's published constraints so we fail fast
# locally instead of round-tripping to the API for a 400).
# ---------------------------------------------------------------------------
MAX_IMAGE_MEGAPIXELS = 64    # width * height
MIN_IMAGE_DIMENSION = 8      # px; Sightengine rejects anything smaller

# ---------------------------------------------------------------------------
# Detection thresholds.
# ---------------------------------------------------------------------------
AI_THRESHOLD = 50.0
LABEL_THRESHOLDS: list[tuple[float, str]] = [
    (85.0, "AI Generated"),
    (60.0, "Likely AI Generated"),
    (45.0, "Suspicious / Inconclusive"),
    (20.0, "Likely Real"),
]
DEFAULT_LABEL = "Real Photo"

SE_STRONG = 90.0
SE_PARTIAL = 60.0
DEEPFAKE_HIGH = 90.0
DEEPFAKE_SUSPICIOUS = 50.0
JPEG_HEAVY_COMPRESSION = 25

AI_SOFTWARE_NAMES = [
    "stable diffusion", "dall-e", "dall·e", "midjourney", "adobe firefly",
    "firefly", "imagen", "comfyui", "automatic1111", "novelai", "invokeai",
    "generative", "ai-generated",
]

_HIVE_BASE_CLASSES = {
    "ai_generated", "not_ai_generated",
    "deepfake", "not_deepfake", "none",
    "inconclusive", "inconclusive_video",
    "ai_generated_audio", "not_ai_generated_audio",
}


def _read_image_signals(image_path: str) -> tuple[int, int, dict, float | None]:
    """Open the file once and pull everything we need: size, EXIF, JPEG quantization."""
    with Image.open(image_path) as img:
        width, height = img.size
        img_format = img.format

        exif_data = img.getexif()
        if exif_data:
            exif = {TAGS.get(tag_id, tag_id): value for tag_id, value in exif_data.items()}
            metadata = {
                "has_exif": True,
                "camera": str(exif.get("Model", "Unknown")),
                "software": str(exif.get("Software", "Unknown")),
            }
        else:
            metadata = {"has_exif": False, "camera": "Unknown", "software": "Unknown"}

        quant_avg = None
        if img_format == "JPEG" and getattr(img, "quantization", None):
            luma = img.quantization.get(0, [])
            if luma:
                quant_avg = sum(luma) / len(luma)

    return width, height, metadata, quant_avg


def _hive_attributions(image_path: str) -> dict[str, float]:
    """Call Hive purely to extract per-generator attribution."""
    try:
        response = hive_classify(image_path)
    except Exception as e:
        logger.warning("Hive attribution lookup failed: %s", e)
        return {}

    output = response.get("output", [])
    if not output:
        return {}
    classes = output[0].get("classes", [])
    attributions: dict[str, float] = {}
    for item in classes:
        cls_name = item.get("class", "")
        val = item.get("value", 0.0)
        if cls_name and cls_name not in _HIVE_BASE_CLASSES and val > 0.01:
            attributions[cls_name] = val * 100.0
    return attributions


def predict_image(image_path: str) -> tuple[str, float, list[str], dict, dict]:
    """Sightengine for the verdict; Hive cascade for attribution when AI-flagged."""
    try:
        width, height, metadata, quant_avg = _read_image_signals(image_path)
    except Exception as e:
        logger.error("Could not read image %s: %s", image_path, e)
        return "Error", 0.0, ["Could not read image file."], {}, {
            "has_exif": False, "camera": "Unknown", "software": "Unknown"
        }

    megapixels = (width * height) / 1_000_000
    if megapixels > MAX_IMAGE_MEGAPIXELS:
        return (
            "Error",
            0.0,
            [f"Image is too large ({width}x{height}px, {megapixels:.1f} MP). "
             f"Maximum is {MAX_IMAGE_MEGAPIXELS} MP total."],
            {},
            metadata,
        )

    if width < MIN_IMAGE_DIMENSION or height < MIN_IMAGE_DIMENSION:
        return (
            "Error",
            0.0,
            [f"Image is too small ({width}x{height}px). "
             f"Each side must be at least {MIN_IMAGE_DIMENSION}px."],
            {},
            metadata,
        )

    try:
        se_response = sightengine_classify(image_path)
    except Exception as e:
        logger.error("Sightengine API integration error: %s", e)
        return (
            "Error",
            0.0,
            ["Detection service unavailable. Please check your network connection or API credentials."],
            {},
            metadata,
        )

    if se_response.get("status") != "success":
        err = se_response.get("error", {})
        msg = err.get("message", "Unknown error from detection service.")
        return "Error", 0.0, [f"Detection service error: {msg}"], {}, metadata

    type_block = se_response.get("type", {})
    ai_generated_raw = type_block.get("ai_generated")
    if ai_generated_raw is None:
        return (
            "Error",
            0.0,
            ["Invalid response format from classification service."],
            {},
            metadata,
        )

    ai_score = float(ai_generated_raw) * 100.0
    deepfake_raw = type_block.get("deepfake")
    deepfake_score = float(deepfake_raw) * 100.0 if deepfake_raw is not None else None

    image_is_ai = ai_score >= AI_THRESHOLD

    # Cascade: only burn a Hive call when Sightengine flagged the image as AI.
    hive_attributions = _hive_attributions(image_path) if image_is_ai else {}
    top_engine: str | None = None
    top_engine_pct: float = 0.0
    if hive_attributions:
        top_engine, top_engine_pct = max(hive_attributions.items(), key=lambda kv: kv[1])

    signals: dict[str, float] = {"Sightengine AI Classifier": round(ai_score, 1)}
    if deepfake_score is not None:
        signals["Sightengine Deepfake"] = round(deepfake_score, 1)

    for engine_name, engine_pct in hive_attributions.items():
        signals[f"Attribution ({engine_name})"] = round(engine_pct, 1)

    reasons: list[str] = []

    # 1. Sightengine AI generated verdict
    if ai_score >= SE_STRONG:
        reasons.append("❌ Sightengine Detector: Strong AI generation signature detected.")
    elif ai_score >= SE_PARTIAL:
        reasons.append("⚠️ Sightengine Detector: Some AI-generation features present.")
    else:
        reasons.append("✅ Sightengine Detector: No strong AI-generation signature.")

    # 2. Generator attribution (via Hive lookup) when image is judged AI
    if image_is_ai:
        if top_engine:
            reasons.append(f"🤖 Generator (via Hive): Most likely '{top_engine}' ({top_engine_pct:.0f}% confidence).")
        else:
            reasons.append("🤖 Generator: AI-generated, but Hive could not identify a specific engine.")

    # 3. Deepfake detection indicators
    if deepfake_score is not None:
        if deepfake_score >= DEEPFAKE_HIGH:
            reasons.append("❌ Deepfake Check: High probability of visual deepfake (face swap).")
        elif deepfake_score >= DEEPFAKE_SUSPICIOUS:
            reasons.append("⚠️ Deepfake Check: Suspicious face-swap patterns detected.")

    # 4. EXIF camera and software metadata
    if not metadata["has_exif"]:
        reasons.append("❌ Metadata Check: No camera data found — typical of downloaded or AI images.")
    else:
        reasons.append(f"✅ Metadata Check: Camera model '{metadata['camera']}' detected.")

    software_val = metadata.get("software", "Unknown").lower()
    if software_val not in ("unknown", "") and any(kw in software_val for kw in AI_SOFTWARE_NAMES):
        reasons.append(f"❌ Metadata Check: Software tag reads '{metadata['software']}' — a known AI generation tool.")

    # 5. JPEG compression heaviness disclaimer
    if quant_avg is not None and quant_avg > JPEG_HEAVY_COMPRESSION:
        reasons.append("⚠️ Compression Check: Image is heavily compressed — result may be less reliable.")

    # 6. Final label, driven by Sightengine's score against LABEL_THRESHOLDS.
    label = DEFAULT_LABEL
    for cutoff, name in LABEL_THRESHOLDS:
        if ai_score >= cutoff:
            label = name
            break

    return label, round(ai_score, 2), reasons, signals, metadata
```

---

## A.3 `backend/ai_model/sightengine_client.py` — Sightengine HTTP wrapper

A thin client around Sightengine's `/check.json` endpoint. Reads credentials from environment variables (loaded by `app.py`'s `load_dotenv()` at startup), sends the image as multipart form data with `models=genai,deepfake`, and returns the parsed JSON response. Any HTTP error, network timeout, or missing-credential condition raises an exception that the orchestrator in `model.py` catches and turns into a user-readable `Error` verdict.

```python
import os
import requests

SIGHTENGINE_API_URL = "https://api.sightengine.com/1.0/check.json"
TIMEOUT_SECONDS = 60


def classify_image(image_path: str) -> dict:
    """
    POSTs the image to Sightengine's /check.json with the 'genai' and 'deepfake'
    models. Each model counts as one operation against your monthly quota.
    Returns the parsed JSON response.
    """
    api_user = os.environ.get("SIGHTENGINE_API_USER")
    api_secret = os.environ.get("SIGHTENGINE_API_SECRET")
    if not api_user or not api_secret:
        raise RuntimeError(
            "SIGHTENGINE_API_USER / SIGHTENGINE_API_SECRET not found in environment variables. "
            "Please check your .env file."
        )

    with open(image_path, "rb") as f:
        data = {
            "models": "genai,deepfake",
            "api_user": api_user,
            "api_secret": api_secret,
        }
        files = {"media": f}
        response = requests.post(
            SIGHTENGINE_API_URL,
            data=data,
            files=files,
            timeout=TIMEOUT_SECONDS,
        )

    response.raise_for_status()
    return response.json()
```

---

## A.4 `backend/ai_model/hive_client.py` — Hive HTTP wrapper

The companion client for Hive's V3 AI-Generated and Deepfake Content Detection endpoint. Functionally identical in structure to the Sightengine wrapper: read credentials, send multipart, return parsed JSON. Hive uses a Bearer-token Authorization header rather than form-data credentials. The orchestrator in `model.py` calls this client only when Sightengine has already judged the image as AI.

```python
import os
import requests

HIVE_API_URL = "https://api.thehive.ai/api/v3/hive/ai-generated-and-deepfake-content-detection"
TIMEOUT_SECONDS = 60

def classify_image(image_path: str) -> dict:
    """
    POSTs the image to Hive's AI-Generated and Deepfake Content Detection V3 Playground API.
    Uses multipart/form-data with the parameter 'media'.
    Returns the parsed JSON response.
    """
    hive_api_key = os.environ.get("HIVE_API_KEY")
    if not hive_api_key:
        raise RuntimeError("HIVE_API_KEY not found in environment variables. Please check your .env file.")

    with open(image_path, "rb") as f:
        headers = {
            "Authorization": f"Bearer {hive_api_key}"
        }
        files = {
            "media": f
        }
        response = requests.post(
            HIVE_API_URL,
            headers=headers,
            files=files,
            timeout=TIMEOUT_SECONDS
        )

    response.raise_for_status()
    return response.json()
```

---

## A.5 `backend/evaluate.py` — Evaluation harness

The evaluation pipeline that produces the metrics quoted in chapter 7. Parses ground-truth labels out of the markdown table in `Test/README.md`, runs every labelled image through the same `predict_image()` function the live application uses, computes the confusion matrix and accuracy / precision / recall / F1, and writes both a machine-readable JSON file and a dissertation-ready Markdown report. The harness supports **resume from cache**: a previous partial run that exhausted the daily API quota can be completed in a subsequent run, which only re-calls the API for images that previously errored.

```python
"""
TrueSight evaluation harness.

Reads ground-truth labels from Test/README.md (the "Expected" column of the
markdown table), runs each labelled image through the detection pipeline,
and produces:

    1. A human-readable summary on stdout
    2. evaluation_results.json   — machine-readable per-image record
    3. evaluation_report.md      — dissertation-ready Markdown report
"""

import os
import re
import sys
import json
import time
from dataclasses import dataclass, asdict, field
from typing import Optional


BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
sys.path.insert(0, BACKEND_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

from ai_model.model import predict_image, AI_THRESHOLD


GROUND_TRUTH_FILE = os.path.join(PROJECT_ROOT, "Test", "README.md")
TEST_DIR = os.path.join(PROJECT_ROOT, "Test")
RESULTS_JSON = os.path.join(PROJECT_ROOT, "evaluation_results.json")
RESULTS_MD = os.path.join(PROJECT_ROOT, "evaluation_report.md")


@dataclass
class Result:
    filename: str
    true_label: str
    predicted_label: str
    verbose_verdict: str
    ai_score: float
    deepfake_score: Optional[float] = None
    top_engine: Optional[str] = None
    correct: bool = False
    error: Optional[str] = None
    reasons: list[str] = field(default_factory=list)


# Ground-truth parsing
_TABLE_ROW = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*([^|]+?)\s*\|")


def parse_ground_truth(readme_path: str) -> dict[str, str]:
    """Extract {filename: 'ai' | 'real'} from Test/README.md."""
    truth: dict[str, str] = {}
    with open(readme_path, encoding="utf-8") as f:
        for line in f:
            m = _TABLE_ROW.match(line)
            if not m:
                continue
            fname = m.group(1).strip()
            expected = m.group(2).strip().lower()
            if expected.startswith("real"):
                truth[fname] = "real"
            elif expected.startswith("ai"):
                truth[fname] = "ai"
    return truth


# Single-image evaluation
_ATTRIBUTION_KEY = re.compile(r"^Attribution \(([^)]+)\)$")


def evaluate_one(filename: str, true_label: str) -> Result:
    path = os.path.join(TEST_DIR, filename)
    if not os.path.exists(path):
        return Result(filename=filename, true_label=true_label,
                      predicted_label="real", verbose_verdict="Error",
                      ai_score=0.0, correct=False,
                      error=f"File not found: {path}")

    try:
        label, score, reasons, signals, _metadata = predict_image(path)
    except Exception as e:
        return Result(filename=filename, true_label=true_label,
                      predicted_label="real", verbose_verdict="Error",
                      ai_score=0.0, correct=False, error=str(e))

    if label == "Error":
        return Result(filename=filename, true_label=true_label,
                      predicted_label="real", verbose_verdict="Error",
                      ai_score=0.0, correct=False, reasons=reasons,
                      error="; ".join(reasons) if reasons else "predict_image returned Error")

    predicted = "ai" if score >= AI_THRESHOLD else "real"

    top_engine = None
    top_engine_score = -1.0
    for key, value in signals.items():
        m = _ATTRIBUTION_KEY.match(key)
        if m and value > top_engine_score:
            top_engine_score = value
            top_engine = m.group(1)

    return Result(
        filename=filename, true_label=true_label,
        predicted_label=predicted, verbose_verdict=label,
        ai_score=score,
        deepfake_score=signals.get("Sightengine Deepfake"),
        top_engine=top_engine,
        correct=(predicted == true_label),
        reasons=reasons,
    )


# Aggregate metrics
def confusion_matrix(results: list[Result]) -> dict[str, int]:
    """Treat 'ai' as the positive class."""
    return {
        "tp": sum(1 for r in results if r.true_label == "ai" and r.predicted_label == "ai"),
        "fp": sum(1 for r in results if r.true_label == "real" and r.predicted_label == "ai"),
        "fn": sum(1 for r in results if r.true_label == "ai" and r.predicted_label == "real"),
        "tn": sum(1 for r in results if r.true_label == "real" and r.predicted_label == "real"),
    }


def metrics(cm: dict[str, int]) -> dict[str, float]:
    tp, fp, fn, tn = cm["tp"], cm["fp"], cm["fn"], cm["tn"]
    total = tp + fp + fn + tn
    accuracy = (tp + tn) / total if total else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"accuracy": accuracy, "precision": precision, "recall": recall, "f1": f1}


# Resume capability
def load_cached_results(json_path: str) -> dict[str, Result]:
    """Load successfully-completed results from a previous run so they can be reused."""
    if not os.path.exists(json_path):
        return {}
    try:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"  (could not load previous results from {json_path}: {e})")
        return {}

    cached: dict[str, Result] = {}
    for r in data.get("results", []):
        if r.get("error"):
            continue
        cached[r["filename"]] = Result(
            filename=r["filename"],
            true_label=r["true_label"],
            predicted_label=r["predicted_label"],
            verbose_verdict=r["verbose_verdict"],
            ai_score=r["ai_score"],
            deepfake_score=r.get("deepfake_score"),
            top_engine=r.get("top_engine"),
            correct=r["correct"],
            error=r.get("error"),
            reasons=r.get("reasons", []),
        )
    return cached


# (Output helpers — print_table, write_markdown_report — and main() omitted
#  here for brevity; see GitHub repository for the full file. The structure
#  is: print live progress, write JSON results, write Markdown report.)
```

> The full `evaluate.py` is approximately 400 lines including the output helpers and the `main()` entry point. The version shown above contains the essential structural code (the dataclass, the parser, the per-image evaluator, the metrics, the resume-from-cache loader). The complete source is in the public GitHub repository (URL in Appendix C).

---

## A.6 Frontend code

The frontend is intentionally framework-free and consists of three files:

- `frontend/index.html` (~230 lines) — single-page application shell.
- `frontend/script.js` (~650 lines) — all client behaviour: upload handling, drag-and-drop, theme toggling, modal management, history rendering, signal display.
- `frontend/style.css` (~1,400 lines) — light and dark theme tokens, layout, responsive breakpoints, animations.

These three files are not included inline in this appendix to keep the page count manageable. They are published in full in the project's public GitHub repository — the URL appears in Appendix C — and the project's `README.md` and `docs/ARCHITECTURE.md` provide a section-by-section guided tour.

---

## A.7 Other repository files

The following additional files exist in the repository and are referenced for completeness:

- `backend/verify_sightengine.py` — manual smoke test that exercises the pipeline against a known-AI sample to verify credentials are configured correctly. Not invoked by the running application.
- `backend/requirements.txt` — five pinned dependencies.
- `backend/.env.example` — placeholder credentials file showing the three required environment variables.
- `start.bat` — Windows one-click launcher.
- `Test/` — the 59-image evaluation set described in chapter 7.
- `evaluation_report.md`, `evaluation_results.json` — outputs of the most recent evaluation run.
- `docs/ARCHITECTURE.md`, `docs/VIVA_QUESTIONS.md` — supporting documentation.

All of the above are accessible from the GitHub repository URL given in Appendix C.
