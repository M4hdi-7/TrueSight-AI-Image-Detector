from PIL import Image
from PIL.ExifTags import TAGS
from .sightengine_client import classify_image

MAX_IMAGE_DIMENSION = 8000  # pixels — beyond this PIL risks running out of memory

# Known AI generation tool names that may appear in an image's EXIF Software tag
AI_SOFTWARE_NAMES = [
    "stable diffusion", "dall-e", "dall·e", "midjourney", "adobe firefly",
    "firefly", "imagen", "comfyui", "automatic1111", "novelai", "invokeai",
    "generative", "ai-generated",
]


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
    Analyzes an image using Sightengine's AI-Generated Image Detection API
    integrated with local EXIF metadata inspection.

    Returns:
        label:      str   — headline verdict ("AI Generated", "Likely Real", etc.)
        score:      float — 0.0–100.0 representing AI likelihood %
        reasons:    list  — human-readable bullet points for the forensic report
        signals:    dict  — per-signal breakdown for the UI (scores mapped as percentages)
        metadata:   dict  — EXIF summary {"has_exif": bool, "camera": str, "software": str}
    """
    try:
        width, height, metadata, quant_avg = _read_image_signals(image_path)
    except Exception as e:
        print(f"ERROR reading image: {e}")
        return "Error", 0.0, ["Could not read image file."], {}, {
            "has_exif": False, "camera": "Unknown", "software": "Unknown"
        }

    if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
        return (
            "Error",
            0.0,
            [f"Image is too large ({width}x{height}px). Maximum is {MAX_IMAGE_DIMENSION}px per side."],
            {},
            metadata,
        )

    try:
        se_response = classify_image(image_path)
    except Exception as e:
        print(f"Sightengine API integration error: {e}")
        return (
            "Error",
            0.0,
            ["Detection service unavailable. Please check your network connection or API credentials."],
            {},
            metadata,
        )

    if se_response.get("status") != "success":
        err = se_response.get("error", {})
        msg = err.get("message", "Unknown error from detection service.")
        return "Error", 0.0, [f"Detection service error: {msg}"], {}, metadata

    type_block = se_response.get("type", {})
    ai_generated_raw = type_block.get("ai_generated")
    if ai_generated_raw is None:
        return (
            "Error",
            0.0,
            ["Invalid response format from classification service."],
            {},
            metadata,
        )

    ai_score = float(ai_generated_raw) * 100.0
    generators = type_block.get("ai_generators", {}) or {}

    # Build UI signals
    signals = {"Sightengine AI Classifier": round(ai_score, 1)}

    # Surface per-generator attributions above a noise floor
    for gen_name, gen_val in generators.items():
        try:
            val_pct = float(gen_val) * 100.0
        except (TypeError, ValueError):
            continue
        if val_pct > 1.0:
            signals[f"Attribution ({gen_name})"] = round(val_pct, 1)

    reasons = []

    # 1. Sightengine AI generated verdict
    if ai_score >= 90:
        reasons.append("❌ Sightengine Detector: Strong AI generation signature detected.")
    elif ai_score >= 60:
        reasons.append("⚠️ Sightengine Detector: Some AI-generation features present.")
    else:
        reasons.append("✅ Sightengine Detector: No strong AI-generation signature.")

    # 2. Top generator attribution if confident
    if generators:
        top_gen, top_val = max(
            ((k, float(v)) for k, v in generators.items() if isinstance(v, (int, float))),
            key=lambda kv: kv[1],
            default=(None, 0.0),
        )
        if top_gen and top_val * 100.0 >= 50:
            reasons.append(f"⚠️ Attribution: Output resembles '{top_gen}' generator.")

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
