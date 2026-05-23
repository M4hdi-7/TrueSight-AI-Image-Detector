import logging

from PIL import Image
from PIL.ExifTags import TAGS

from .sightengine_client import classify_image as sightengine_classify
from .hive_client import classify_image as hive_classify

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Input limits (mirror Sightengine's published constraints so we fail fast
# locally instead of round-tripping to the API for a 400).
# ---------------------------------------------------------------------------
MAX_IMAGE_MEGAPIXELS = 64    # width * height
MIN_IMAGE_DIMENSION = 8      # px; Sightengine rejects anything smaller

# ---------------------------------------------------------------------------
# Detection thresholds. Adjust here rather than at the call sites so verdict
# logic stays auditable in one place.
# ---------------------------------------------------------------------------

# Above this Sightengine score we judge the image as AI and trigger the (more
# expensive) Hive lookup for generator attribution. Below this we skip Hive
# entirely so real photos don't burn Hive quota.
AI_THRESHOLD = 50.0

# Verdict labels — keyed by the minimum ai_score (descending) that triggers each.
LABEL_THRESHOLDS: list[tuple[float, str]] = [
    (85.0, "AI Generated"),
    (60.0, "Likely AI Generated"),
    (45.0, "Suspicious / Inconclusive"),
    (20.0, "Likely Real"),
]
DEFAULT_LABEL = "Real Photo"

# Reason-text cutoffs (percent).
SE_STRONG = 90.0
SE_PARTIAL = 60.0
DEEPFAKE_HIGH = 90.0
DEEPFAKE_SUSPICIOUS = 50.0   # Sightengine docs treat > 0.5 as deepfake
JPEG_HEAVY_COMPRESSION = 25  # average luma quantization

# Known AI generation tool names that may appear in an image's EXIF Software tag
AI_SOFTWARE_NAMES = [
    "stable diffusion", "dall-e", "dall·e", "midjourney", "adobe firefly",
    "firefly", "imagen", "comfyui", "automatic1111", "novelai", "invokeai",
    "generative", "ai-generated",
]

# Hive classes that describe the verdict itself, not a generator engine.
# Anything outside this set in Hive's classes[] is treated as a candidate
# engine attribution (gpt-4o, midjourney, flux, etc.).
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


def _hive_attributions(image_path: str) -> dict[str, float]:
    """
    Call Hive purely to extract per-generator attribution. Returns a dict of
    {engine_name: probability_pct}. Returns {} on any failure — Hive is a
    best-effort enrichment here, not a hard dependency.
    """
    try:
        response = hive_classify(image_path)
    except Exception as e:
        logger.warning("Hive attribution lookup failed: %s", e)
        return {}

    output = response.get("output", [])
    if not output:
        return {}
    classes = output[0].get("classes", [])
    attributions: dict[str, float] = {}
    for item in classes:
        cls_name = item.get("class", "")
        val = item.get("value", 0.0)
        if cls_name and cls_name not in _HIVE_BASE_CLASSES and val > 0.01:
            attributions[cls_name] = val * 100.0
    return attributions


def predict_image(image_path: str) -> tuple[str, float, list[str], dict, dict]:
    """
    Uses Sightengine as the primary detector for AI-generation and deepfake
    scores. When Sightengine judges the image as AI (ai_score >= AI_THRESHOLD),
    Hive is called as a secondary lookup purely to extract generator
    attribution (which Sightengine's current plan does not return).

    Returns:
        label:    str   — headline verdict ("AI Generated", "Likely Real", ...)
        score:    float — 0.0–100.0 AI likelihood %, from Sightengine
        reasons:  list  — human-readable bullet points
        signals:  dict  — per-signal breakdown for the UI
        metadata: dict  — EXIF summary
    """
    try:
        width, height, metadata, quant_avg = _read_image_signals(image_path)
    except Exception as e:
        logger.error("Could not read image %s: %s", image_path, e)
        return "Error", 0.0, ["Could not read image file."], {}, {
            "has_exif": False, "camera": "Unknown", "software": "Unknown"
        }

    megapixels = (width * height) / 1_000_000
    if megapixels > MAX_IMAGE_MEGAPIXELS:
        return (
            "Error",
            0.0,
            [
                f"Image is too large ({width}x{height}px, {megapixels:.1f} MP). "
                f"Maximum is {MAX_IMAGE_MEGAPIXELS} MP total."
            ],
            {},
            metadata,
        )

    if width < MIN_IMAGE_DIMENSION or height < MIN_IMAGE_DIMENSION:
        return (
            "Error",
            0.0,
            [
                f"Image is too small ({width}x{height}px). "
                f"Each side must be at least {MIN_IMAGE_DIMENSION}px."
            ],
            {},
            metadata,
        )

    try:
        se_response = sightengine_classify(image_path)
    except Exception as e:
        logger.error("Sightengine API integration error: %s", e)
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

    deepfake_raw = type_block.get("deepfake")
    deepfake_score = float(deepfake_raw) * 100.0 if deepfake_raw is not None else None

    image_is_ai = ai_score >= AI_THRESHOLD

    # Cascade: only burn a Hive call when Sightengine flagged the image as AI.
    hive_attributions = _hive_attributions(image_path) if image_is_ai else {}
    top_engine: str | None = None
    top_engine_pct: float = 0.0
    if hive_attributions:
        top_engine, top_engine_pct = max(hive_attributions.items(), key=lambda kv: kv[1])

    # Build UI signals
    signals: dict[str, float] = {"Sightengine AI Classifier": round(ai_score, 1)}
    if deepfake_score is not None:
        signals["Sightengine Deepfake"] = round(deepfake_score, 1)

    # Surface Hive's attribution engines so the UI renders them as
    # "🤖 AI Engine: <name>" rows (the existing frontend regex picks these up).
    for engine_name, engine_pct in hive_attributions.items():
        signals[f"Attribution ({engine_name})"] = round(engine_pct, 1)

    reasons: list[str] = []

    # 1. Sightengine AI generated verdict
    if ai_score >= SE_STRONG:
        reasons.append("❌ Sightengine Detector: Strong AI generation signature detected.")
    elif ai_score >= SE_PARTIAL:
        reasons.append("⚠️ Sightengine Detector: Some AI-generation features present.")
    else:
        reasons.append("✅ Sightengine Detector: No strong AI-generation signature.")

    # 2. Generator attribution (via Hive lookup) when image is judged AI
    if image_is_ai:
        if top_engine:
            reasons.append(f"🤖 Generator (via Hive): Most likely '{top_engine}' ({top_engine_pct:.0f}% confidence).")
        else:
            reasons.append("🤖 Generator: AI-generated, but Hive could not identify a specific engine.")

    # 3. Deepfake detection indicators
    if deepfake_score is not None:
        if deepfake_score >= DEEPFAKE_HIGH:
            reasons.append("❌ Deepfake Check: High probability of visual deepfake (face swap).")
        elif deepfake_score >= DEEPFAKE_SUSPICIOUS:
            reasons.append("⚠️ Deepfake Check: Suspicious face-swap patterns detected.")

    # 4. EXIF camera and software metadata
    if not metadata["has_exif"]:
        reasons.append("❌ Metadata Check: No camera data found — typical of downloaded or AI images.")
    else:
        reasons.append(f"✅ Metadata Check: Camera model '{metadata['camera']}' detected.")

    software_val = metadata.get("software", "Unknown").lower()
    if software_val not in ("unknown", "") and any(kw in software_val for kw in AI_SOFTWARE_NAMES):
        reasons.append(f"❌ Metadata Check: Software tag reads '{metadata['software']}' — a known AI generation tool.")

    # 5. JPEG compression heaviness disclaimer
    if quant_avg is not None and quant_avg > JPEG_HEAVY_COMPRESSION:
        reasons.append("⚠️ Compression Check: Image is heavily compressed — result may be less reliable.")

    # 6. Final label, driven by Sightengine's score against LABEL_THRESHOLDS.
    label = DEFAULT_LABEL
    for cutoff, name in LABEL_THRESHOLDS:
        if ai_score >= cutoff:
            label = name
            break

    return label, round(ai_score, 2), reasons, signals, metadata
