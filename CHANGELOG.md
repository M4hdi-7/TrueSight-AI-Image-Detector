# Changelog

## v1.2 — Sightengine primary + Hive attribution cascade

- **Sightengine becomes the primary detector.** A single `models=genai,deepfake` call covers both AI-generation and face-swap detection. Sightengine's score drives the headline verdict.
- **Hive is repositioned as a cost-aware fallback.** It's only called when Sightengine flags an image as AI (`ai_score >= 50%`), and purely to extract per-engine attribution (`midjourney`, `gpt-4o`, `flux`, …) that Sightengine doesn't return on the current API plan.
- **Local input limits match Sightengine's exactly:** 12 MB file size, 64 megapixel total, 8 px per side minimum, formats JPEG / PNG / WEBP / BMP / TIFF / JPEG 2000.
- **Threshold configuration lifted to a single block** at the top of `backend/ai_model/model.py` (`AI_THRESHOLD`, `LABEL_THRESHOLDS`, `SE_STRONG`, `DEEPFAKE_HIGH`, …) so verdict calibration is auditable in one place.
- **`logging` replaces `print()`** throughout the backend. Set `LOG_LEVEL=DEBUG` for verbose output.
- **Frontend static assets** consolidated under `frontend/assets/`. Verdict copy updated to reflect the dual-provider flow.
- **Pinned dependencies** in `backend/requirements.txt` for reproducible installs.

## v1.1 — Hive AI integration

- Removed the local 5-model PyTorch jury (no more `torch`, `transformers`, or ONNX).
- Migrated detection to Hive AI's V3 AI-Generated and Deepfake Content Detection Playground API.
- Added per-engine attribution surfaced as separate UI signals (`gpt-4o`, `midjourney`, `flux`, etc.).
- Frontend dark mode, drag-and-drop, PWA manifest, and accessibility pass (ARIA roles, focus management, reduced-motion).
- Persisted SQLite history with newest-50 read cap and a `/clear_history` endpoint.

## v1.0 — Local 5-model jury

- Bundled five locally-run image classification models (CNN + transformer variants) and aggregated their votes into a single verdict.
- Heavy install footprint (`torch`, `transformers`, `onnxruntime`), CPU-bound inference, and large model weight files.
- Initial Flask + vanilla JS architecture established here.
