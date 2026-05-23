# Appendix B: Screenshots of the System's Screens

The screenshots below demonstrate every major user-facing screen of TrueSight. Each is captioned with the operational context in which it was captured.

## B.1 Home screen and upload zone

`[INSERT SCREENSHOT: 01-home-upload-zone.png]`

The home screen presents a single primary action — a drag-and-drop upload zone that accepts JPEG, PNG, WEBP, BMP, and TIFF images up to 12 MB. The left-hand panel describes the system's role and lists its four headline features: dual-API detection, generator attribution, EXIF metadata inspection, and a local scan history.

## B.2 Verdict card on an AI-generated image

`[INSERT SCREENSHOT: 02-verdict-ai.png]`

A verdict card produced on a known Midjourney sample. Sightengine returns 99.0 percent confidence, placing the verdict in the "AI Generated" label bucket. The card animates in below the upload zone and remains visible until the user clears it or uploads another image.

## B.3 Detection details modal

`[INSERT SCREENSHOT: 03-details-modal.png]`

The detection details modal exposes every signal that contributed to the verdict — the Sightengine AI Classifier score, the deepfake score, every Hive attribution row, the EXIF camera-and-software summary, and the bullet-point reasons list. This transparency is the distinguishing feature against cloud detectors that return only an opaque score.

## B.4 Verdict on a real photograph

`[INSERT SCREENSHOT: 04-verdict-real.png]`

The verdict card for an authentic Unsplash photograph. Sightengine returns 0.1 percent, placing the verdict in the "Real Photo" bucket. The Hive cascade was not invoked because the AI-generation threshold was not crossed, and no attribution rows are present.

## B.5 History tab

`[INSERT SCREENSHOT: 05-history-tab.png]`

The history tab fetches the most recent fifty scans from the local SQLite database. Each row shows a thumbnail served from `backend/uploads/`, the verdict label, the confidence percentage, and the timestamp.

## B.6 Oversized-upload error

`[INSERT SCREENSHOT: 06-error-oversized.png]`

The frontend enforces the 12 MB upload cap client-side and surfaces the violation as a toast notification before any network request leaves the browser, protecting the user's quota with no round-trip to the backend.

## B.7 Dark theme

`[INSERT SCREENSHOT: 07-dark-theme.png]`

The dark theme is implemented through CSS custom properties on the `:root` and `[data-theme="dark"]` selectors. The chosen theme persists across sessions in `localStorage` and is applied before first paint, preventing a flash of the wrong theme on dark-mode reload.

## B.8 Mobile / phone view

`[INSERT SCREENSHOT: 08-mobile-home.png]`

`[INSERT SCREENSHOT: 09-mobile-verdict.png]`

`[INSERT SCREENSHOT: 10-mobile-history.png]`

The same TrueSight web interface viewed from a phone connected to the same Wi-Fi network as the host machine. The layout is responsive — the upload zone fills the viewport width, navigation collapses for narrower screens, the verdict card and signal modal stack vertically, and the history entries render as single-column cards. No mobile-specific code path exists; the same HTML, CSS, and JavaScript serve both desktop and mobile, with breakpoints driven by CSS media queries. This is the LAN-accessibility scenario described in the use cases — a user captures or receives an image on their phone and analyses it through the browser without needing to transfer the file to the host machine first.
