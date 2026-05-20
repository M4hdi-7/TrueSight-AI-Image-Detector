from PIL import Image
from PIL.ExifTags import TAGS
from .hive_client import classify_image

MAX_IMAGE_DIMENSION = 8000  # pixels — beyond this PIL risks running out of memory

# Known AI generation tool names that may appear in an image's EXIF Software tag
AI_SOFTWARE_NAMES = [
    "stable diffusion", "dall-e", "dall·e", "midjourney", "adobe firefly",
    "firefly", "imagen", "comfyui", "automatic1111", "novelai", "invokeai",
    "generative", "ai-generated",
]

# Hive classes that describe the verdict itself, not the generator engine.
# Anything outside this set is treated as a candidate engine attribution.
_HIVE_BASE_CLASSES = {
    "ai_generated", "not_ai_generated",
    "deepfake", "not_deepfake", "none",
    "inconclusive", "inconclusive_video",
    "ai_generated_audio", "not_ai_generated_audio",
}


def _read_image_signals(image_path: str) -> tuple[int, int, dict, float | None]:
    """Open the file once and pull everything we need: size, EXIF, JPEG quantization."""
    with Image.open(image_path) as img:
        width, height = img.size
        img_format = img.format

        exif_data = img.getexif()
        if exif_data:
            exif = {TAGS.get(tag_id, tag_id): value for tag_id, value in exif_data.items()}
            metadata = {
                "has_exif": True,
                "camera": str(exif.get("Model", "Unknown")),
                "software": str(exif.get("Software", "Unknown")),
            }
        else:
            metadata = {"has_exif": False, "camera": "Unknown", "software": "Unknown"}

        quant_avg = None
        if img_format == "JPEG" and getattr(img, "quantization", None):
            luma = img.quantization.get(0, [])
            if luma:
                quant_avg = sum(luma) / len(luma)

    return width, height, metadata, quant_avg


def predict_image(image_path: str) -> tuple[str, float, list[str], dict, dict]:
    """
    Analyzes an image using Hive's AI-Generated and Deepfake Content Detection V3 API
    integrated with local EXIF metadata inspection.

    Returns:
        label:      str   — headline verdict ("AI Generated", "Likely Real", etc.)
        score:      float — 0.0–100.0 representing AI likelihood %
        reasons:    list  — human-readable bullet points for the forensic report
        signals:    dict  — per-signal breakdown for the UI (mutually exclusive scores mapped as percentages)
        metadata:   dict  — EXIF summary {"has_exif": bool, "camera": str, "software": str}
    """
    try:
        width, height, metadata, quant_avg = _read_image_signals(image_path)
    except Exception as e:
        print(f"ERROR reading image: {e}")
        return "Error", 0.0, ["Could not read image file."], {}, {
            "has_exif": False, "camera": "Unknown", "software": "Unknown"
        }

    # Reject absurdly large images before API upload to avoid transmission and process overhead
    if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
        return (
            "Error",
            0.0,
            [f"Image is too large ({width}x{height}px). Maximum is {MAX_IMAGE_DIMENSION}px per side."],
            {},
            metadata,
        )

    try:
        hive_response = classify_image(image_path)
    except Exception as e:
        print(f"Hive API integration error: {e}")
        return (
            "Error",
            0.0,
            ["Detection service unavailable. Please check your network connection or API key."],
            {},
            metadata,
        )

    output = hive_response.get("output", [])
    if not output:
        return (
            "Error",
            0.0,
            ["Invalid response format from classification service."],
            {},
            metadata,
        )

    classes = output[0].get("classes", [])
    scores = {item["class"]: item["value"] * 100 for item in classes if "class" in item and "value" in item}

    ai_score = scores.get("ai_generated", 0.0)
    deepfake_score = scores.get("deepfake", 0.0)

    # Build UI signals (flat dictionary of {signal_name: score_percentage})
    signals = {}
    if "ai_generated" in scores:
        signals["Hive AI Classifier"] = round(scores["ai_generated"], 1)
    if "deepfake" in scores:
        signals["Visual Deepfake Head"] = round(scores["deepfake"], 1)

    # Dynamically surface any generator-attribution heads Hive returns (value > 1.0%).
    # This catches new engines (e.g. gptimage2) without hardcoding them.
    for item in classes:
        cls_name = item.get("class", "")
        val = item.get("value", 0.0) * 100
        if cls_name not in _HIVE_BASE_CLASSES and val > 1.0:
            signals[f"Attribution ({cls_name})"] = round(val, 1)

    reasons = []

    # 1. Hive AI generated verdicts
    if ai_score >= 90:
        reasons.append("❌ Hive Detector: Strong AI generation signature detected.")
    elif ai_score >= 60:
        reasons.append("⚠️ Hive Detector: Some AI-generation features present.")
    else:
        reasons.append("✅ Hive Detector: No strong AI-generation signature.")

    # 2. Deepfake detection indicators
    if deepfake_score >= 90:
        reasons.append("❌ Deepfake Check: High probability of visual deepfake (face swap).")
    elif deepfake_score >= 60:
        reasons.append("⚠️ Deepfake Check: Suspicious face-swap patterns detected.")

    # 3. EXIF camera and software metadata
    if not metadata["has_exif"]:
        reasons.append("❌ Metadata Check: No camera data found — typical of downloaded or AI images.")
    else:
        reasons.append(f"✅ Metadata Check: Camera model '{metadata['camera']}' detected.")

    software_val = metadata.get("software", "Unknown").lower()
    if software_val not in ("unknown", "") and any(kw in software_val for kw in AI_SOFTWARE_NAMES):
        reasons.append(f"❌ Metadata Check: Software tag reads '{metadata['software']}' — a known AI generation tool.")

    # 4. JPEG compression heaviness disclaimer
    if quant_avg is not None and quant_avg > 25:
        reasons.append("⚠️ Compression Check: Image is heavily compressed — result may be less reliable.")

    # 5. Final label using TrueSight thresholds
    if ai_score >= 85:
        label = "AI Generated"
    elif ai_score >= 60:
        label = "Likely AI Generated"
    elif ai_score >= 45:
        label = "Suspicious / Inconclusive"
    elif ai_score >= 20:
        label = "Likely Real"
    else:
        label = "Real Photo"

    return label, round(ai_score, 2), reasons, signals, metadata
