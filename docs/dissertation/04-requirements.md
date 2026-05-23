# 4. Requirements Phase

This chapter enumerates the functional and non-functional requirements that the system was designed to satisfy.

## 4.1 Functional requirements

The functional requirements describe what the system must *do*. They are written as testable statements; every requirement below maps to behaviour visible at the API surface or in the user interface.

| ID | Requirement |
| --- | --- |
| **FR-1** | The system shall accept a single image file uploaded by the user through the web interface, via either drag-and-drop or a file picker. |
| **FR-2** | The system shall validate the uploaded file's extension against a whitelist (JPEG, PNG, WEBP, BMP, TIFF, JPEG 2000) and reject any other format with a user-facing error message. |
| **FR-3** | The system shall verify the uploaded file's actual format by reading its first bytes (magic-byte check), independently of the declared file extension, and reject files whose contents do not match a supported image format. |
| **FR-4** | The system shall reject any image larger than 12 MB or whose width × height exceeds 64 megapixels, in alignment with Sightengine's documented input limits. |
| **FR-5** | The system shall reject any image whose width or height is below 8 pixels. |
| **FR-6** | The system shall classify each accepted image using Sightengine's `genai` and `deepfake` models, obtaining an AI-generation probability and a deepfake (face-swap) probability for the image. |
| **FR-7** | When the AI-generation probability exceeds the configured threshold (50%), the system shall additionally call Hive AI to obtain per-engine generator attribution. The system shall not call Hive when the image is judged real. |
| **FR-8** | The system shall extract EXIF metadata from the image and surface the camera model and software tag, when present, in the forensic report. |
| **FR-9** | The system shall inspect the JPEG quantization table (when the image is a JPEG) and produce a "heavily compressed" disclaimer in the forensic report when the average luma quantization exceeds 25. |
| **FR-10** | The system shall produce a verdict label drawn from the set {AI Generated, Likely AI Generated, Suspicious / Inconclusive, Likely Real, Real Photo} based on the AI-generation score and the documented label thresholds. |
| **FR-11** | The system shall return a forensic report consisting of a verdict label, a numeric confidence score, a list of human-readable reasons, a dictionary of per-signal scores, and an EXIF metadata summary. |
| **FR-12** | The system shall persist every successful scan to a local SQLite database, recording filename, verdict, confidence, reasons, and timestamp. |
| **FR-13** | The system shall provide a history view that returns the most recent 50 scans, in reverse chronological order. |
| **FR-14** | The system shall provide a mechanism to clear all scan history and delete all stored upload files in a single user-initiated action. |
| **FR-15** | The system shall serve uploaded images back to the frontend through a dedicated route so that history entries can display thumbnails. |
| **FR-16** | The system shall display, in the user interface, the AI-generation score, the deepfake score, every per-engine attribution returned by Hive (when applicable), the EXIF metadata summary, and the bullet-point forensic reasons. |
| **FR-17** | The system shall be reachable from any device on the same local-area network — the backend listens on `0.0.0.0` so that a phone, laptop, or tablet connected to the same Wi-Fi can use the interface. |
| **FR-18** | The system shall provide a one-click launcher (`start.bat`) that starts both backend and frontend servers, detects the host's LAN IP, and displays the URL to open. |
| **FR-19** | The system shall provide an automated evaluation harness that reads a ground-truth-labelled test set, runs every labelled image through the detection pipeline, and produces a confusion matrix together with accuracy, precision, recall, and F1 metrics. |
| **FR-20** | The evaluation harness shall support resume-from-cache behaviour: a partial run that exhausts the API quota or fails partway can be re-executed and will only re-call the API for images that previously errored. |

## 4.2 Non-functional requirements

Non-functional requirements describe how the system behaves rather than what it does.

### 4.2.1 Performance

| ID | Requirement |
| --- | --- |
| **NFR-1** | A single detection request shall complete within 60 seconds end-to-end. The Sightengine API call is the dominant latency component, typically 5–10 seconds; the Hive cascade adds up to 30 seconds for AI-positive images. |
| **NFR-2** | Image-validation failures (extension, size, dimension) shall return a 400-class HTTP response within 1 second, without invoking any external API. |
| **NFR-3** | The history endpoint shall return within 200 ms — the table is capped at 50 rows and requires no joins. |

### 4.2.2 Security

| ID | Requirement |
| --- | --- |
| **NFR-4** | The system shall sanitise all uploaded filenames using `werkzeug.utils.secure_filename` before storage, and shall rename every file to a fresh UUID, preventing path-traversal attacks and ensuring no original filename is ever persisted to disk. |
| **NFR-5** | The system shall enforce a magic-byte format check on every uploaded file after extension validation, deleting any file whose claimed extension does not match its actual content. |
| **NFR-6** | API responses (excluding `/uploads/*`) shall include `Cache-Control: no-store` headers to prevent stale data being served from the browser cache. |
| **NFR-7** | API credentials (Sightengine user/secret, Hive key) shall be loaded from a `.env` file that is never committed to version control. The project ships a `.env.example` containing placeholder values only. |

### 4.2.3 Reliability

| ID | Requirement |
| --- | --- |
| **NFR-8** | A failure of the Hive attribution call shall not block the verdict. The system shall degrade gracefully, producing a verdict based on Sightengine alone with a note that attribution was unavailable. |
| **NFR-9** | A failure of the Sightengine call shall produce a synthetic `Error` verdict with a user-readable reason, rather than a server crash or an unhandled exception. |
| **NFR-10** | Database errors during history retrieval shall not crash the request; the system returns an empty list and logs the failure server-side. |
| **NFR-11** | The evaluation harness shall continue running after a per-image error (e.g. daily-quota exhaustion), record the failure in the results file, and allow a subsequent resume run to retry only the failed entries. |

### 4.2.4 Usability and accessibility

| ID | Requirement |
| --- | --- |
| **NFR-12** | The user interface shall be operable with keyboard alone — every interactive element shall be reachable via Tab and activatable via Enter or Space. |
| **NFR-13** | The user interface shall include ARIA roles and labels for the upload zone, tab navigation, modal dialogs, and result displays, supporting assistive technology. |
| **NFR-14** | The interface shall respect the user's `prefers-reduced-motion` setting; non-essential animation shall be suppressed when this preference is active. |
| **NFR-15** | The interface shall provide a light and a dark theme, with the user's selection persisted to `localStorage` and applied before first paint to avoid a theme-flash on dark-mode reloads. |
| **NFR-16** | The interface shall be responsive — fully usable on a mobile browser at 360-pixel viewport width as well as a desktop browser at 1920 pixels. |

### 4.2.5 Maintainability

| ID | Requirement |
| --- | --- |
| **NFR-17** | All detection thresholds (binary classification cutoff, verdict-label brackets, deepfake severity bands, JPEG compression cutoff) shall be defined as named constants in a single block at the top of `backend/ai_model/model.py`, so that calibration changes require only one file edit. |
| **NFR-18** | The system shall be provider-agnostic in architecture: each external detection API is encapsulated behind a thin HTTP-client module, and the orchestration logic in `model.py` is the only file that knows which providers are called. |
| **NFR-19** | All Python dependencies shall be pinned to exact versions in `requirements.txt` for reproducible installation. |
| **NFR-20** | The system shall use the standard `logging` module rather than `print()` for diagnostic output, with verbosity controllable through a `LOG_LEVEL` environment variable. |

### 4.2.6 Portability

| ID | Requirement |
| --- | --- |
| **NFR-21** | The backend shall depend on no machine-learning libraries (no `torch`, `transformers`, or `onnxruntime`). Detection is entirely API-driven; the only image-handling dependency is Pillow. |
| **NFR-22** | The frontend shall be a static HTML / CSS / JavaScript application with no build step, no transpiler, and no framework runtime — editable directly. |
| **NFR-23** | The system shall run on any operating system that supports Python 3.10+. The Windows-only one-click launcher (`start.bat`) is provided for convenience but is not the only way to start the system. |
