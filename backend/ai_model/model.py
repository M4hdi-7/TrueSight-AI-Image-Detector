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

def predict_image(image_path: str) -> tuple[str, float, list[str], dict]:
    """
    Analyzes an image using Hive's AI-Generated and Deepfake Content Detection V3 API
    integrated with local EXIF metadata inspection.
    
    Returns:
        label:      str   — headline verdict ("AI Generated", "Likely Real", etc.)
        score:      float — 0.0–100.0 representing AI likelihood %
        reasons:    list  — human-readable bullet points for the forensic report
        signals:    dict  — per-signal breakdown for the UI (mutually exclusive scores mapped as percentages)
    """
    try:
        pil_image = Image.open(image_path).convert("RGB")
        width, height = pil_image.size
        
        # Reject absurdly large images before API upload to avoid transmission and process overhead
        if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
            return (
                "Error",
                0.0,
                [f"Image is too large ({width}x{height}px). Maximum is {MAX_IMAGE_DIMENSION}px per side."],
                {},
            )
            
        # Call Hive V3 API
        try:
            hive_response = classify_image(image_path)
        except Exception as e:
            print(f"Hive API integration error: {e}")
            return (
                "Error",
                0.0,
                ["Detection service unavailable. Please check your network connection or API key."],
                {}
            )
            
        # Parse output classes
        output = hive_response.get("output", [])
        if not output:
            return (
                "Error",
                0.0,
                ["Invalid response format from classification service."],
                {}
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
            
        # Dynamically extract and format specific generator attribution heads if they are detected (value > 1.0%)
        # This ensures we catch any new engines Hive adds (like gptimage2) without hardcoding them.
        base_classes = {
            "ai_generated", "not_ai_generated", 
            "deepfake", "not_deepfake", "none",
            "inconclusive", "inconclusive_video",
            "ai_generated_audio", "not_ai_generated_audio"
        }
        for item in classes:
            cls_name = item.get("class", "")
            val = item.get("value", 0.0) * 100
            if cls_name not in base_classes and val > 1.0:
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
            
        # 3. EXIF camera and software metadata validation
        meta = extract_metadata(image_path)
        if not meta["has_exif"]:
            reasons.append("❌ Metadata Check: No camera data found — typical of downloaded or AI images.")
        else:
            reasons.append(f"✅ Metadata Check: Camera model '{meta['camera']}' detected.")
            
        software_val = meta.get("software", "Unknown").lower()
        if software_val not in ("unknown", "") and any(kw in software_val for kw in AI_SOFTWARE_NAMES):
            reasons.append(f"❌ Metadata Check: Software tag reads '{meta['software']}' — a known AI generation tool.")
            
        # Compress / GAN Noise disclaimer for JPEGs
        try:
            raw_img = Image.open(image_path)
            if raw_img.format == "JPEG" and hasattr(raw_img, "quantization") and raw_img.quantization:
                luma = raw_img.quantization.get(0, [])
                if luma and (sum(luma) / len(luma)) > 25:
                    reasons.append("⚠️ Compression Check: Image is heavily compressed — result may be less reliable.")
        except Exception as e:
            print(f"JPEG quality check failed: {e}")
            
        # 4. Determine final label using standard TrueSight thresholds
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
            
        return label, round(ai_score, 2), reasons, signals

    except Exception as e:
        print(f"ERROR inside predict_image: {e}")
        return "Error", 0.0, ["Analysis failed due to server error."], {}

def extract_metadata(image_path: str) -> dict:
    try:
        image = Image.open(image_path)
        # Use the public getexif() API (Pillow 6+) instead of deprecated _getexif()
        exif_data = image.getexif()

        if not exif_data:
            return {"has_exif": False, "camera": "Unknown", "software": "Unknown"}

        exif = {TAGS.get(tag_id, tag_id): value for tag_id, value in exif_data.items()}

        return {
            "has_exif": True,
            "camera": str(exif.get("Model", "Unknown")),
            "software": str(exif.get("Software", "Unknown")),
        }
    except Exception as e:
        print(f"EXIF extraction failed: {e}")
        return {"has_exif": False, "camera": "Unknown", "software": "Unknown"}
