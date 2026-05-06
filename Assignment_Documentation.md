# TrueSight (v1.0) - Implementation & Design Documentation

## 1. Create Tables: Provide Samples (4 points)

The TrueSight application utilizes a local SQLite database to log and manage all previous scans. The core architecture relies on a single relational table named `history` to store the analysis results.

### Database Engine
**SQLite3**

### Table Schema (SQL)
```sql
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    result TEXT NOT NULL,
    confidence REAL,
    reasons TEXT,
    timestamp TEXT
);
```

### Data Sample
Below is a sample of the data inserted into the database after an image has been successfully evaluated by the AI Jury system:

| id | filename | result | confidence | reasons | timestamp |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `1` | `a1b2c3d4e5.jpg` | `AI Generated (5/5 Experts Agree)` | `98.5` | `["❌ Style Check: It has the smooth, 'perfect' look of AI art.", "❌ Pixel Check: The pixels don't align like a normal photo."]` | `2026-05-04 15:30` |

---

## 2. Design UI: Provide main screen (5 points)

The TrueSight user interface is designed to be intuitive, responsive, and clear, abstracting the complexity of the underlying AI models from the end user.

> **[PLACEHOLDER: Insert a screenshot of the main "Home" tab of the application here. The screenshot should show the upload drop-zone, the navigation tabs, and the "Analyze Image" button.]**

### Main Screen Components:
1.  **Navigation System:** A top-level tab bar that allows the user to seamlessly toggle between the active scanning interface ("Home") and their saved database logs ("History").
2.  **Upload Zone:** A prominent drag-and-drop container explicitly restricting file inputs to valid image types (JPEG, PNG, WEBP) and enforcing a 16MB file size limit.
3.  **Action Button:** The primary "Analyze Image" trigger, which enforces validation by remaining disabled until a supported file is securely loaded into the DOM.
4.  **Dynamic Results View:** A hidden UI component that activates upon receiving a payload from the backend. It features a visual confidence progress bar, the final textual verdict, and a "View Forensic Details" button.

> **[PLACEHOLDER: (Optional) Insert a second screenshot showing the UI after an image has been scanned, displaying the confidence bar and the "View Forensic Details" modal.]**

---

## 3. Implement 80% of the system functions (Prototype) (6 points)

During the prototype phase, the core functionality required to establish a working pipeline from the user's browser to the local machine learning models was successfully implemented.

**Core Prototype Features:**
*   **Secure Image Ingestion (Backend):** Developed a Flask REST API (`/predict` POST route) that accepts `multipart/form-data`. The system validates file extensions against a strict whitelist, generates a secure UUID filename to prevent collisions, and commits the file to the local `uploads/` directory.
*   **Base AI Integration:** Successfully integrated Hugging Face pipeline models via PyTorch. The backend opens the saved image using the Pillow library, converts it to RGB, and passes it through an image-classification neural network to generate an initial "AI vs. Real" confidence score.
*   **Cross-Origin Communication:** Established a CORS-enabled architecture allowing the local HTML/JS/CSS frontend to send asynchronous `fetch` requests to the Python backend and dynamically inject the returned JSON verdicts into the DOM without requiring a page reload.

---

## 4. Finishing the implementation (5 points)

The final implementation phase elevated the project from a functional prototype to a robust, highly accurate AI forensic tool by introducing complex logic, state management, and edge-case handling.

**Final Polish & Advanced Features:**
*   **5-Model Jury Architecture:** Replaced the single-model prototype with a weighted ensemble of five distinct AI models (Face, Style, Pattern, Pixel, and Generalist). This drastically reduces false positives by requiring a consensus among different neural networks.
*   **Explainable AI & Metadata Analysis:** Engineered logic to generate human-readable explanations based on specific model confidence thresholds. Additionally, implemented EXIF data extraction to identify known AI software tags (e.g., "Midjourney") and detect missing camera metadata as supplementary fake signals.
*   **Persistent History Management:** Finalized the integration of the SQLite `history.db`. Built the `/history` GET route to populate the frontend table with past scans, and the `/clear_history` DELETE route to allow users to permanently erase both database rows and local media files for privacy.
*   **Security & Stability Measures:** Implemented a Pillow "magic byte" inspection on upload to prevent malicious users from bypassing the extension filter by simply renaming files. Added a `MAX_IMAGE_DIMENSION` ceiling to prevent massive images from crashing the AI models due to Out-Of-Memory (OOM) errors.
