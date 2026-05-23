# 4. Requirements Phase

## 4.1 Functional requirements

| ID | Requirement |
| --- | --- |
| **FR-1** | The system shall accept an image upload through the web interface via drag-and-drop or a file picker, restricted to JPEG, PNG, WEBP, BMP, TIFF, and JPEG 2000 formats up to 12 MB and 64 megapixels. |
| **FR-2** | The system shall validate every upload through five sequential checks — extension whitelist, `secure_filename` sanitisation, UUID rename, PIL magic-byte format verification, and dimension cap — rejecting any file that fails before contacting an external service. |
| **FR-3** | The system shall classify each accepted image using Sightengine's `genai` and `deepfake` models, obtaining an AI-generation probability and a face-swap probability. |
| **FR-4** | When the AI-generation probability is at least 50 percent, the system shall additionally call Hive AI to extract per-engine generator attribution. When the probability is below this threshold the system shall not contact Hive. |
| **FR-5** | The system shall compute local forensic signals on every image: EXIF camera and software tag extraction, detection of known AI-generation software names in the EXIF Software field, and a JPEG-quantization heuristic that flags heavily-compressed images. |
| **FR-6** | The system shall produce a verdict consisting of a label drawn from {AI Generated, Likely AI Generated, Suspicious / Inconclusive, Likely Real, Real Photo}, a confidence percentage, a list of plain-language reasons, and a dictionary of per-signal scores. |
| **FR-7** | The system shall persist every successful scan to a local SQLite database, recording filename, verdict, confidence, reasons, and timestamp, and shall expose the most recent fifty scans through a history endpoint. |
| **FR-8** | The system shall provide a single user action that wipes the entire scan history and deletes every uploaded image file. |
| **FR-9** | The system shall be reachable from any device on the same local-area network, with the backend binding to `0.0.0.0` and the frontend computing the backend URL from the request hostname. |
| **FR-10** | The system shall provide an automated evaluation harness that reads ground-truth labels, runs every labelled image through the detection pipeline, computes accuracy / precision / recall / F1 plus a confusion matrix, and supports resume from cache after partial failure. |

## 4.2 Non-functional requirements

| ID | Requirement |
| --- | --- |
| **NFR-1** | A single detection request shall complete within 60 seconds. Validation failures shall return within 1 second without contacting any external API. |
| **NFR-2** | Uploaded filenames shall be sanitised with `werkzeug.utils.secure_filename` and replaced with a UUID before storage, preventing path-traversal attacks and ensuring no original filename is persisted. |
| **NFR-3** | API responses (excluding `/uploads/*`) shall include `Cache-Control: no-store`. API credentials shall be loaded from a `.env` file that is gitignored; the repository ships a `.env.example` containing placeholders only. |
| **NFR-4** | Failure of the Hive attribution call shall not block the verdict — the system shall degrade gracefully to a Sightengine-only result. Failure of the Sightengine call shall produce a user-readable Error verdict without crashing. |
| **NFR-5** | The user interface shall be fully operable from the keyboard, expose ARIA roles for the upload zone, tab navigation, and modal dialogs, and respect the user's `prefers-reduced-motion` setting. |
| **NFR-6** | The interface shall offer light and dark themes, persisted to `localStorage` and applied before first paint, and shall be responsive from 360-pixel mobile viewports up to desktop widths. |
| **NFR-7** | All detection thresholds — binary classification cutoff, verdict-label brackets, deepfake severity bands, JPEG compression cutoff — shall be defined as named constants in a single block at the top of `backend/ai_model/model.py`. |
| **NFR-8** | The detection backend shall be provider-agnostic: each external API is encapsulated behind a thin HTTP client, with the orchestration logic in `model.py` as the only file that knows which providers are called. |
| **NFR-9** | All Python dependencies shall be pinned to exact versions in `requirements.txt`. The backend shall depend on no machine-learning libraries; image handling uses Pillow only. |
| **NFR-10** | The system shall use the standard `logging` module rather than `print()` for diagnostic output, with verbosity controllable through a `LOG_LEVEL` environment variable. |
