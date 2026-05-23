# Appendix B: Screenshots of the System's Screens

This appendix collects screenshots demonstrating every major user-facing screen of TrueSight. Each screenshot is captioned with the operational context that produced it.

> **NOTE TO THE STUDENT**: This file is a capture checklist. Take each screenshot in the order listed, save it under `docs/dissertation/screenshots/` with the suggested filename, and then replace each placeholder block below with an actual `![caption](path)` Markdown image reference. After all seven are captured, delete this note.

## Capture checklist

For each screenshot below, follow these steps:
1. Start TrueSight (`.\start.bat`).
2. Reach the state described in the **Setup** instructions.
3. Capture the visible area using your platform's screenshot tool (Windows: `Win + Shift + S`; macOS: `Cmd + Shift + 4`).
4. Save the file under `docs/dissertation/screenshots/` with the filename in the table.
5. Replace the `[INSERT SCREENSHOT: ...]` placeholder in the corresponding section below with the actual image markdown.

| # | Filename | Description |
| - | -------- | ----------- |
| 1 | `01-home-upload-zone.png` | Home tab showing the drag-and-drop upload zone, intro panel, accepted formats, and 12 MB cap text. Light theme. |
| 2 | `02-verdict-ai.png` | Verdict card for a clear AI image (recommend `Test/Midjourney-for-Beginners-...jpg`). Shows the "AI Generated" headline, the confidence percentage, and the progress bar. |
| 3 | `03-details-modal.png` | Detection-details modal open on the same scan as #2. Shows the bullet-point reasons list, the per-signal scores including Sightengine AI Classifier, Sightengine Deepfake, and at least one "🤖 AI Engine" attribution row. |
| 4 | `04-verdict-real.png` | Verdict card on a real photograph (recommend `Test/Dwayne_Johnson_2014_(cropped).jpg`). Shows "Real Photo" headline with a low confidence percentage. No attribution rows. |
| 5 | `05-history-tab.png` | History tab showing several past scans. Each entry has a thumbnail, verdict label, confidence percentage, and timestamp. The "Clear History" button is visible. |
| 6 | `06-error-oversized.png` | Toast notification that appears when attempting to upload a file larger than 12 MB. (To produce a file > 12 MB for testing, use any large image or generate one with `dd` / PowerShell.) |
| 7 | `07-dark-theme.png` | Dark theme variant of the home tab, demonstrating that the theme toggle persists across the entire UI. |

(Optional: an eighth screenshot taken on a mobile browser, demonstrating the responsive layout at a 360-pixel viewport width.)

## Screenshot 1 — Home screen and upload zone

**Setup**: Open the application URL (e.g. `http://192.168.1.7:8000`) in a desktop browser at light theme. Make sure the Home tab is selected. Show the upload zone, the intro panel ("AI-Generated Image Detection" heading, the four feature bullets), and the "Powered by Sightengine + Hive attribution" tag.

`[INSERT SCREENSHOT: docs/dissertation/screenshots/01-home-upload-zone.png]`

**Caption**: The TrueSight home screen presents a single primary action — a drag-and-drop upload zone that accepts JPEG, PNG, WEBP, BMP, and TIFF images up to 12 MB. The left-hand panel describes the system's role and the four headline features: dual-API detection, generator attribution, EXIF metadata inspection, and a local scan history.

## Screenshot 2 — Verdict on an AI-generated image

**Setup**: Upload a known AI image (e.g. one of the Gemini samples). Wait for the verdict card to animate in. The card shows the verdict text, the confidence percentage, the progress bar, and the "View Detection Details" button.

`[INSERT SCREENSHOT: docs/dissertation/screenshots/02-verdict-ai.png]`

**Caption**: A verdict card produced on a known Midjourney sample. Sightengine returns 99.0% confidence, placing the verdict in the "AI Generated" label bucket. The card animates in below the upload zone and remains visible until the user clears it or uploads another image.

## Screenshot 3 — Detection details modal

**Setup**: With the verdict card from Screenshot 2 visible, click **View Detection Details**. The modal opens with the full breakdown.

`[INSERT SCREENSHOT: docs/dissertation/screenshots/03-details-modal.png]`

**Caption**: The detection details modal exposes every signal that contributed to the verdict — the Sightengine AI Classifier score, the deepfake score, every Hive attribution row (one per generator engine that scored above the noise floor), the EXIF camera-and-software summary, and the bullet-point reasons list. This transparency is what distinguishes TrueSight from cloud detectors that return only an opaque score.

## Screenshot 4 — Verdict on a real photograph

**Setup**: Upload a real photo (e.g. one of the Unsplash samples). Wait for the verdict card.

`[INSERT SCREENSHOT: docs/dissertation/screenshots/04-verdict-real.png]`

**Caption**: The verdict card for an authentic Unsplash photograph. Sightengine returns 0.1% confidence, placing the verdict in the "Real Photo" label bucket. Because the AI-generation threshold was not crossed, the Hive cascade was not invoked and no attribution rows are present in the signals list.

## Screenshot 5 — History tab

**Setup**: Click the History tab in the navigation bar. The list of recent scans appears, newest first.

`[INSERT SCREENSHOT: docs/dissertation/screenshots/05-history-tab.png]`

**Caption**: The history tab fetches the most recent fifty scans from the local SQLite database. Each row shows a thumbnail served from `backend/uploads/`, the verdict label, the confidence percentage, and the timestamp of the scan. The "Clear History" action wipes both the database table and the uploads directory in a single user-initiated operation.

## Screenshot 6 — Oversized-upload error

**Setup**: Attempt to upload a file larger than 12 MB (the cap defined by `MAX_FILE_SIZE`). A toast notification appears in the corner without any network activity.

`[INSERT SCREENSHOT: docs/dissertation/screenshots/06-error-oversized.png]`

**Caption**: The frontend enforces the 12 MB upload cap client-side and surfaces the violation as a toast notification before any network request leaves the browser. This protects the user's quota with no round-trip to the backend or the detection APIs.

## Screenshot 7 — Dark theme

**Setup**: Click the theme toggle in the top navigation bar. The interface switches to dark presentation. Take the screenshot of the same home view as #1.

`[INSERT SCREENSHOT: docs/dissertation/screenshots/07-dark-theme.png]`

**Caption**: The dark theme is implemented entirely through CSS custom properties on the `:root` and `[data-theme="dark"]` selectors. The chosen theme persists across sessions in `localStorage` and is applied before first paint, preventing the brief "flash of unstyled content" that naive theme implementations exhibit on dark-mode reload.
