# 7. Implementation Phase

This chapter describes the technical realisation of the design: the languages, the libraries, the development tools, the user-facing screens, the operational scenarios, and the sample reports produced by the system.

## 7.1 Languages used

| Layer | Language | Why this choice |
| --- | --- | --- |
| **Backend** | Python 3.10+ | Flask is the lightest production-acceptable web framework in the ecosystem; PIL handles every supported image format; `requests` covers the HTTP-client need; `dotenv` handles configuration. The Python 3.10 baseline enables modern type hints (`tuple[int, int, ...]`, `dict[str, float]`) without `typing` imports. |
| **Frontend** | HTML5 / CSS3 / Vanilla JavaScript (ES2020) | The application is a single page with a small number of dynamic states (upload, result, history, modal). A framework would add a build step, runtime overhead, and onboarding friction without functional benefit. Vanilla JavaScript with module-level state is the right size for the problem. |
| **Persistence** | SQLite (SQL) | Single-file database, zero administration, ships with Python. Schema is one table. There are no concurrency or replication requirements that would justify a server database. |
| **Configuration** | dotenv (key = value text) | Standard, language-agnostic format for environment-variable injection. |
| **Markup of generated reports** | Markdown | The evaluation harness produces Markdown reports because Markdown renders natively on GitHub and converts cleanly to Word, PDF, and LaTeX. |

## 7.2 Tools used

### 7.2.1 Backend runtime dependencies

Pinned in `backend/requirements.txt` to exact versions for reproducible installation:

| Package | Version | Role |
| --- | --- | --- |
| `Flask` | 3.1.2 | HTTP server and routing |
| `flask-cors` | 6.0.2 | Cross-origin request handling for LAN access |
| `pillow` | 12.0.0 | Image opening, format detection, EXIF parsing, JPEG quantization access |
| `requests` | 2.32.5 | HTTP client for Sightengine and Hive calls |
| `python-dotenv` | 1.2.2 | Loading API credentials from `.env` |

There are intentionally **no machine-learning libraries** — no `torch`, `transformers`, `onnxruntime`, `numpy`, or `scikit-learn`. Detection is API-driven; the only image-handling library is Pillow.

### 7.2.2 External services

| Service | Endpoint | Purpose |
| --- | --- | --- |
| Sightengine | `https://api.sightengine.com/1.0/check.json` | Primary detector: AI-generation probability and deepfake probability per image, called with `models=genai,deepfake`. Free tier: 2,000 operations per month, 500 per day. |
| Hive AI | V3 AI-generated and deepfake content detection endpoint | Secondary attribution lookup — called only when Sightengine flags an image as AI. Returns per-engine classification heads (Midjourney, DALL·E, Flux, Gemini, etc.). |

### 7.2.3 Development tools

| Tool | Use |
| --- | --- |
| **Visual Studio Code** | Primary editor, including the Mermaid extension for diagram preview during dissertation writing. |
| **Git + GitHub** | Version control, pull-request workflow, public repository hosting. The project's full history is preserved on the `sighteng` branch of the public repo. |
| **Browser developer tools** (Chrome / Firefox) | UI debugging, network inspection, responsive-design preview for mobile breakpoints. |
| **PowerShell + Windows Terminal** | Backend launch, virtual environment management, test runs. |
| **Mermaid Live Editor** (https://mermaid.live) | Rendering the diagrams embedded in chapters 5 and 6 to PNG / SVG for inclusion in the final document. |

### 7.2.4 Project structure

The repository layout (excerpt) is:

```
backend/
    app.py                      Flask routes and orchestration
    ai_model/
        model.py                Detection pipeline
        sightengine_client.py   Sightengine HTTP wrapper
        hive_client.py          Hive HTTP wrapper
    evaluate.py                 Evaluation harness with resume capability
    verify_sightengine.py       Manual smoke test
    requirements.txt
    .env.example
frontend/
    index.html
    script.js
    style.css
    manifest.json
    assets/                     Icons, logos, PWA images
Test/                           Manually-curated evaluation set
    README.md                   Ground-truth labels
docs/
    ARCHITECTURE.md
    VIVA_QUESTIONS.md
    dissertation/               (this chapter and the others)
start.bat                       Windows launcher
README.md
CHANGELOG.md
LICENSE
evaluation_report.md
evaluation_results.json
```

## 7.3 Templates

The project intentionally uses no templating framework on either side:

- **No backend template engine** — the Flask backend serves pure JSON. There is no Jinja2 template rendering. This keeps the backend's responsibility narrow: handle uploads, run the detection pipeline, persist results, return JSON.
- **No frontend framework** — there is no React, Vue, Svelte, Angular, or any other framework runtime. The DOM is manipulated directly in vanilla JavaScript. CSS uses custom properties (CSS variables) for the light and dark theme tokens.

This is a deliberate choice motivated by the project's lightness goal — the v1.0 ancestor used heavy ML dependencies and the v1.2 design explicitly inverts that posture, with the simplest stack that satisfies every requirement.

## 7.4 Screenshots of the system

> **Screenshots are listed in Appendix B.** This subsection embeds them at the right places in the chapter once they have been captured. For each, capture using Windows + Shift + S or your platform's equivalent, save into `docs/dissertation/screenshots/`, and replace the placeholder below with an image link.

### 7.4.1 Home screen with the upload zone

`[INSERT SCREENSHOT: docs/dissertation/screenshots/01-home-upload-zone.png]`

The home screen presents a single primary action: a large drag-and-drop upload zone. The accepted formats and the 12 MB cap are shown below the icon. The left-hand panel describes the project in two sentences and lists its four headline features.

### 7.4.2 Verdict card on an AI-generated image

`[INSERT SCREENSHOT: docs/dissertation/screenshots/02-verdict-ai.png]`

The verdict card animates in below the upload zone. The headline (e.g. "AI Generated") and the confidence percentage are visible at a glance. A "View Detection Details" button opens the modal with the full signal breakdown.

### 7.4.3 Detection details modal — signals and reasons

`[INSERT SCREENSHOT: docs/dissertation/screenshots/03-details-modal.png]`

The modal contains three sections: the bullet-point reasons list, the per-signal scores (Sightengine AI Classifier, Sightengine Deepfake, every "🤖 AI Engine" attribution row from Hive when applicable), and the EXIF metadata summary (camera model, software tag).

### 7.4.4 Verdict on a real photograph

`[INSERT SCREENSHOT: docs/dissertation/screenshots/04-verdict-real.png]`

Real-photo verdicts label the image "Real Photo" with a low confidence score and no attribution rows. The Hive cascade was not invoked because the Sightengine score did not exceed the 50% threshold.

### 7.4.5 History tab

`[INSERT SCREENSHOT: docs/dissertation/screenshots/05-history-tab.png]`

The history view lists the most recent fifty scans, newest first. Each entry shows the verdict label, the confidence score, the date and time, and a thumbnail. The "Clear History" button at the top of the list wipes both the database table and the uploads folder.

### 7.4.6 Error state — oversized upload

`[INSERT SCREENSHOT: docs/dissertation/screenshots/06-error-oversized.png]`

Attempting to upload a file larger than 12 MB triggers a client-side toast notification before any network request is made. No quota is burned and no file reaches the backend.

### 7.4.7 Dark theme

`[INSERT SCREENSHOT: docs/dissertation/screenshots/07-dark-theme.png]`

The theme toggle in the navigation bar swaps the application between light and dark presentations, both implemented via CSS custom properties on the `:root` and `[data-theme="dark"]` selectors. The chosen theme is persisted to `localStorage` and applied before first paint to prevent a flash of the wrong theme on dark-mode reloads.

## 7.5 Scenarios

Three illustrative scenarios demonstrate end-to-end use of the system.

### 7.5.1 Journalist verifying a viral image

A journalist on assignment receives a forwarded image purporting to show a public figure in an unusual situation. Before publishing, the journalist opens TrueSight on the newsroom's local network from their phone, drops the image into the upload zone, and waits approximately ten seconds. The verdict returns: "AI Generated" at 99% confidence, with the Hive cascade naming Midjourney as the most likely generator. The reasons list highlights the lack of EXIF metadata and the absence of any camera-software tag. The journalist screenshots the verdict for the editorial trail and declines to publish. **The image and the verdict never leave the LAN.**

### 7.5.2 Social-media moderator triaging user uploads

A moderator working through a queue of reported images uses TrueSight as a triage step before more expensive human review. Each upload takes under thirty seconds end-to-end (Sightengine call plus, for AI-flagged images, the Hive cascade). Verdicts in the "AI Generated" or "Likely AI Generated" buckets are routed to a separate handling queue with the attribution preserved; verdicts in the "Real Photo" or "Likely Real" buckets continue down the normal moderation pipeline. The local SQLite history records every triage decision for later audit.

### 7.5.3 AI researcher labelling a dataset

A researcher building a dataset of AI-generated images for downstream training uses TrueSight's `evaluate.py` script to label a directory of candidate samples in bulk. Ground-truth labels are added to `Test/README.md` for any images where the source is known; the harness runs through the rest, produces a confusion matrix, and identifies the cases where TrueSight's verdict disagrees with the researcher's expectation. Those disagreement cases — the "interesting failures" — become the focus of dataset review. The auto-generated `evaluation_report.md` includes a "Failure analysis" section that enumerates every misclassified image with the reasons emitted by the pipeline.

## 7.6 Sample reports

The evaluation harness (`backend/evaluate.py`) produces a Markdown report after each run. The most recent run produced the following summary; the full file appears as `evaluation_report.md` at the repository root.

### 7.6.1 Evaluation methodology

The test set comprised 59 manually-curated images: 40 ground-truth AI-generated samples spanning twelve named generator engines (Midjourney, Flux, DALL·E, GPT-Image v1.5 and v2, Gemini 3, Stable Diffusion, SDXL, Z-Image, Kling, Krea, Ideogram, Grok) plus four "in the wild" Reddit and viral-hoax AI images, and 19 ground-truth real photographs drawn from Unsplash (with photographer attribution in the URL slug), the New York Times CMS, NASA Hubble's public archive, Wikipedia portrait files, Flickr, and iStockphoto. Each image was passed through the full `predict_image()` pipeline. A prediction was classified as **AI** when the Sightengine `ai_generated` score was ≥ 50% and **Real** otherwise.

### 7.6.2 Confusion matrix

AI is treated as the positive class.

|                | Predicted Real | Predicted AI |
| -------------- | -------------- | ------------ |
| **True Real**  | 19 (TN)        | 0 (FP)       |
| **True AI**    | 1 (FN)         | 39 (TP)      |

### 7.6.3 Metrics

| Metric | Value | Interpretation |
| --- | --- | --- |
| Accuracy | **98.3%** | Fraction of correct verdicts overall. |
| Precision | **100.0%** | Of every image TrueSight labelled AI, the fraction that was actually AI. |
| Recall | **97.5%** | Of every truly-AI image in the set, the fraction TrueSight correctly identified. |
| F1 | **98.7%** | Harmonic mean of precision and recall — the headline metric for a class-imbalanced evaluation. |

A note on class imbalance: the test set is 68% AI / 32% real, somewhat skewed. F1 is reported in preference to accuracy because F1 is insensitive to that skew. A naive detector that always says "AI" would achieve 68% accuracy on this set but would have undefined precision and 100% recall — the F1 metric exposes this failure mode that a raw accuracy number conceals.

### 7.6.4 Failure analysis

The single misclassification was the file `its-still-nuts-to-me-how-realistic-ai-is-getting-incredible-v0-bcxd5awmq50h1.webp`. This is an AI-generated image sourced from a Reddit post whose title explicitly described the sample as a generation chosen for exceptional photorealism — an image curated *by humans, for being undetectably AI-looking*. Sightengine returned an AI score of 2.0% on this image, well below the 50% binary threshold, leading to a Real verdict. The reasons list contained only two bullets: a ✅ "no strong AI-generation signature" and a ❌ "no camera metadata found" — that second bullet is the only signal that hints at the true origin.

The case is significant beyond a single data point. It demonstrates the upper bound on what automated AI-image detection can achieve when generative models are specifically optimised to fool human perception, and it argues for layered defences (provenance signatures, EXIF analysis, source verification) rather than reliance on a single classifier head.

### 7.6.5 Observed properties of Sightengine's score distribution

A secondary observation from the evaluation, worth reporting because it informs threshold-calibration decisions: Sightengine's `ai_generated` scores were strongly bimodal. Of the 39 AI images correctly identified, every one received an `ai_generated` score of exactly 99.0%. Of the 19 real photographs, 18 received exactly 0.1% and one received 1.0%. Only a single image in the entire set produced an intermediate score (48.0% on a Kevin Mueller Unsplash photograph), which the verdict layer correctly placed in the "Suspicious / Inconclusive" UI bucket because it fell between the 45% and 60% LABEL_THRESHOLDS.

This bimodality implies that the binary AI-vs-real verdict is largely insensitive to where the threshold is placed within the broad gap; the verdict-label brackets (85/60/45/20) primarily affect the few in-between cases. This observation is honest evidence about the calibration of the upstream API and is something to mention proactively in viva.
