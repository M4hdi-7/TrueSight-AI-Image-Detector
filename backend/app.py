import os
import uuid
import sqlite3
import json
import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from PIL import Image
from ai_model.model import predict_image, extract_metadata
from werkzeug.utils import secure_filename


# --- SETTINGS ---
UPLOAD_FOLDER = "uploads"
DB_FILE = "history.db"
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16 Megabytes

app = Flask(__name__)
CORS(app) # Allow the frontend (phone) to talk to the backend (PC)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE # <--- SAFETY CAP

# Make sure the upload folder exists so we don't get errors
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- DATABASE SETUP ---
# Database removed for full privacy mode (Stateless Backend)

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
            return jsonify({"error": "Invalid file type"}), 400

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
                if img.format not in {"JPEG", "PNG", "WEBP"}:
                    raise ValueError(f"Unexpected format: {img.format}")
        except Exception:
            os.remove(image_path)
            return jsonify({"error": "File is not a valid image."}), 400

        # --- ASK THE AI JURY ---
        label, confidence, reasons, signals = predict_image(image_path)
        metadata = extract_metadata(image_path)
        
        # INSTANTLY DELETE THE FILE FOR FULL PRIVACY
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
        except Exception as e:
            print(f"Failed to delete {image_path}: {e}")

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
        print("SERVER ERROR:", e)
        return jsonify({"error": "Internal server error"}), 500

# History endpoints removed for full privacy mode

# Prevent the browser from saving old versions of the site (Caching)
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

if __name__ == "__main__":
    # Host 0.0.0.0 is crucial so other devices on Wi-Fi can see the server
    app.run(host='0.0.0.0', port=5000, debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true")