# 7. Implementation Phase

## 7.1 Languages used

| Layer | Language | Rationale |
| --- | --- | --- |
| Backend | Python 3.10+ | Flask is the lightest production-acceptable web framework; PIL handles every supported image format; `requests` covers the HTTP client need. Python 3.10 enables modern type hints (`tuple[int, int, ...]`) without `typing` imports. |
| Frontend | HTML5 / CSS3 / Vanilla JavaScript (ES2020) | A single-page application with five dynamic states. A framework would add a build step and runtime overhead without functional benefit. |
| Persistence | SQLite | Single-file database, zero administration, ships with Python. One table, no concurrency. |
| Configuration | dotenv | Standard, language-agnostic format for environment-variable injection. |
| Generated reports | Markdown | The evaluation harness produces Markdown because it renders natively on GitHub and converts cleanly to Word, PDF, and LaTeX. |

## 7.2 Tools used

### 7.2.1 Backend dependencies

Five packages, pinned to exact versions in `backend/requirements.txt`:

| Package | Version | Role |
| --- | --- | --- |
| `Flask` | 3.1.2 | HTTP server and routing |
| `flask-cors` | 6.0.2 | Cross-origin request handling for LAN access |
| `pillow` | 12.0.0 | Image opening, format detection, EXIF parsing, JPEG quantization |
| `requests` | 2.32.5 | HTTP client for Sightengine and Hive |
| `python-dotenv` | 1.2.2 | Loading API credentials from `.env` |

There are intentionally **no machine-learning libraries** — no `torch`, `transformers`, `onnxruntime`, `numpy`, or `scikit-learn`. Detection is API-driven and the only image-handling library is Pillow.

### 7.2.2 External services

| Service | Endpoint | Purpose |
| --- | --- | --- |
| Sightengine | `https://api.sightengine.com/1.0/check.json` | Primary detector — AI-generation and deepfake scores. Free tier 2,000 ops/month, 500/day. |
| Hive AI | V3 AI-Generated and Deepfake Content Detection | Secondary attribution lookup — called only when Sightengine flags an image AI. Returns per-engine classification heads. |

### 7.2.3 Development tools

Visual Studio Code as the primary editor; Git and GitHub for version control and public hosting; browser developer tools for UI inspection and responsive preview; PowerShell on Windows for backend launch and virtual-environment management; Mermaid Live Editor (`mermaid.live`) for rendering the diagrams in this dissertation to PNG.

## 7.3 Templates

The project uses no templating framework on either side. The Flask backend serves pure JSON (no Jinja2). The frontend is plain HTML, CSS, and JavaScript with no React, Vue, Svelte, or Angular runtime. This is a deliberate choice motivated by the project's lightness goal — version 1.0 used heavy ML dependencies and version 1.2 explicitly inverts that posture, choosing the simplest stack that satisfies every requirement.

## 7.4 Screenshots of the system

The seven screenshots listed in Appendix B are inserted at the positions below in the final document.

### 7.4.1 Home screen with the upload zone

`[INSERT SCREENSHOT: 01-home-upload-zone.png]`

The home screen presents a single primary action — a drag-and-drop upload zone that accepts JPEG, PNG, WEBP, BMP, and TIFF images up to 12 MB. The left-hand panel describes the project and lists its four headline features.

### 7.4.2 Verdict card on an AI-generated image

`[INSERT SCREENSHOT: 02-verdict-ai.png]`

A verdict card produced on a known Midjourney sample. Sightengine returns 99.0 percent confidence, placing the verdict in the "AI Generated" label bucket.

### 7.4.3 Detection details modal

`[INSERT SCREENSHOT: 03-details-modal.png]`

The modal exposes every signal that contributed to the verdict — the Sightengine AI Classifier score, the deepfake score, every Hive attribution row, the EXIF camera-and-software summary, and the bullet-point reasons list. This transparency distinguishes TrueSight from cloud detectors that return only an opaque score.

### 7.4.4 Verdict on a real photograph

`[INSERT SCREENSHOT: 04-verdict-real.png]`

The verdict card for an authentic Unsplash photograph. Sightengine returns 0.1 percent, placing the verdict in the "Real Photo" bucket. The Hive cascade was not invoked and no attribution rows are present.

### 7.4.5 History tab

`[INSERT SCREENSHOT: 05-history-tab.png]`

The history tab fetches the most recent fifty scans from the local SQLite database. Each row shows a thumbnail, the verdict label, the confidence percentage, and the timestamp.

### 7.4.6 Oversized-upload error

`[INSERT SCREENSHOT: 06-error-oversized.png]`

The frontend enforces the 12 MB upload cap client-side, surfacing the violation as a toast notification before any network request leaves the browser.

### 7.4.7 Dark theme

`[INSERT SCREENSHOT: 07-dark-theme.png]`

The dark theme is implemented through CSS custom properties on the `:root` and `[data-theme="dark"]` selectors. The chosen theme persists across sessions in `localStorage` and is applied before first paint to prevent a flash of the wrong theme on dark-mode reload.

### 7.4.8 Mobile / phone view

`[INSERT SCREENSHOT: 08-mobile-home.png]`

`[INSERT SCREENSHOT: 09-mobile-verdict.png]`

`[INSERT SCREENSHOT: 10-mobile-history.png]`

The same interface viewed from a phone on the same Wi-Fi network as the host machine. The layout is responsive: the upload zone fills the viewport width, the verdict card and details modal stack vertically, and the history entries render as single-column cards. No mobile-specific code path exists — the same HTML, CSS, and JavaScript serve both form factors, with breakpoints driven by CSS media queries. This is the LAN-accessibility scenario described in chapter 5: a user captures or receives an image on their phone and analyses it directly through the browser without transferring the file to the host machine.

## 7.5 Scenarios

**Journalist verifying a viral image.** A reporter receives a forwarded image of a public figure in an unusual situation. Before publication, the reporter opens TrueSight on the newsroom's local network from a phone, drops the image into the upload zone, and waits roughly ten seconds. The verdict returns "AI Generated" at 99 percent confidence with Midjourney named as the most likely generator. The reasons list highlights the absence of EXIF metadata. The reporter captures the verdict screen for the editorial trail and declines to publish. The image never leaves the LAN.

**Social-media moderator triaging user uploads.** A moderator works through a queue of reported images using TrueSight as a triage step before human review. Each upload completes in under thirty seconds. "AI Generated" and "Likely AI Generated" verdicts are routed to a dedicated review queue with the attribution preserved; "Real Photo" and "Likely Real" verdicts continue down the normal pipeline. The local SQLite history records every triage decision for later audit.

**Researcher labelling a dataset.** A researcher building a dataset of AI-generated images uses TrueSight's `evaluate.py` script to label a directory of candidate samples in bulk. Ground-truth labels are added to `Test/README.md` where the origin is known; the harness runs through the rest and produces a confusion matrix together with a Markdown report listing every misclassification. The disagreement cases — the "interesting failures" — become the focus of dataset review.

## 7.6 Sample reports

The evaluation harness produces a Markdown report after each run. The most recent run is summarised below; the full file is `evaluation_report.md` at the repository root.

### 7.6.1 Methodology

The test set comprised 59 manually-curated images — 40 ground-truth AI-generated samples spanning twelve named generator engines (Midjourney, Flux, DALL·E, GPT-Image v1.5 and v2, Gemini 3, Stable Diffusion, SDXL, Z-Image, Kling, Krea, Ideogram, Grok) plus several Reddit and viral-hoax AI images, and 19 ground-truth real photographs drawn from Unsplash, the New York Times CMS, NASA Hubble's public archive, Wikipedia portrait files, Flickr, and iStockphoto. Each image was passed through the full `predict_image()` pipeline. A prediction was classified as AI when the Sightengine `ai_generated` score was at least 50 percent and real otherwise.

### 7.6.2 Confusion matrix

AI is the positive class.

|                | Predicted Real | Predicted AI |
| -------------- | -------------- | ------------ |
| **True Real**  | 19 (TN)        | 0 (FP)       |
| **True AI**    | 1 (FN)         | 39 (TP)      |

### 7.6.3 Metrics

| Metric | Value | Interpretation |
| --- | --- | --- |
| Accuracy | **98.3 %** | Fraction of correct verdicts overall. |
| Precision | **100.0 %** | Of every image TrueSight labelled AI, the fraction that was actually AI. |
| Recall | **97.5 %** | Of every truly-AI image in the set, the fraction TrueSight correctly identified. |
| F1 | **98.7 %** | Harmonic mean of precision and recall — the headline metric for a class-imbalanced evaluation. |

The set is 68 percent AI and 32 percent real, a moderate imbalance. F1 is reported in preference to accuracy because F1 is insensitive to that skew — a naive detector that always says "AI" would achieve 68 percent accuracy on the same set, exposing a failure mode that the raw accuracy number conceals.

### 7.6.4 Failure analysis

The single misclassification was the file `its-still-nuts-to-me-how-realistic-ai-is-getting-incredible-v0-bcxd5awmq50h1.webp` — an AI-generated image sourced from a Reddit post whose title explicitly described it as a generation chosen for exceptional photorealism. Sightengine returned an AI score of 2.0 percent on this image, well below the 50 percent threshold, leading to a Real verdict. The case is significant beyond a single data point: it demonstrates the upper bound on what automated AI-image detection can achieve when generative models are specifically optimised to fool human perception, and it argues for layered defences (provenance signatures, EXIF analysis, source verification) rather than reliance on a single classifier head.

### 7.6.5 Observed properties of Sightengine's score distribution

A secondary observation from the evaluation: Sightengine's `ai_generated` scores were strongly bimodal. Of the 39 AI images correctly identified, every one received an `ai_generated` score of exactly 99.0 percent. Of the 19 real photographs, 18 received exactly 0.1 percent and one received 1.0 percent. Only a single image in the entire set produced an intermediate score (48.0 percent on an Unsplash photograph). This bimodality implies that the binary AI-vs-real verdict is largely insensitive to where the threshold is placed within the broad gap; the verdict-label brackets (85, 60, 45, 20) primarily affect the few in-between cases.
