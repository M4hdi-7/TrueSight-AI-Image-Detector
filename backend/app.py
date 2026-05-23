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
# This lets your phone see the actual image stored on your PC's hard drive
@app.route('/uploads/<filename>')
def serve_image(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# 2. The Main Brain (Predict)
# This receives the image, runs the AI, and saves the result
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
        # This catches renamed non-image files that pass the extension whitelist.
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
        reasons_json = json.dumps(reasons) # We need to turn the list into text for the database

        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO history (filename, result, confidence, reasons, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (filename, label, confidence, reasons_json, timestamp))
            conn.commit()

        # Send the results back to the frontend
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
# Sends the list of past scans to the phone
@app.route("/history", methods=["GET"])
def get_history():
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row # This lets us select columns by name
            cursor = conn.cursor()
            # Get the last 50 scans, newest first
            cursor.execute("SELECT * FROM history ORDER BY id DESC LIMIT 50")
            rows = cursor.fetchall()

            history_data = []
            for row in rows:
                history_data.append({
                    "id": row["id"],
                    "filename": row["filename"],
                    "result": row["result"],
                    "confidence": row["confidence"],
                    "reasons": json.loads(row["reasons"]), # Turn the text back into a list
                    "timestamp": row["timestamp"]
                })

            return jsonify(history_data)
    except Exception as e:
        logger.error("Failed to read /history: %s", e)
        return jsonify([])

# 4. Wipe Everything
# Deletes images and clears the database
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
