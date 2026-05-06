import torch
from transformers import pipeline
from PIL import Image
from PIL.ExifTags import TAGS

device = 0 if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else -1)

print(f"Initializing TrueSight AI Jury (Loading 5 Models) on device: {device}...")

# --- SET UP THE JURY ---
# We load 5 different "Experts" to vote on the image.

# 1. The Face Expert
face_detector = pipeline("image-classification", model="dima806/deepfake_vs_real_image_detection", device=device)

# 2. The Artistic Expert
modern_detector = pipeline("image-classification", model="Ateeqq/ai-vs-human-image-detector", device=device)

# 3. The Legacy Expert
legacy_detector = pipeline("image-classification", model="umm-maybe/AI-image-detector", device=device)

# 4. The Pixel Specialist
forensic_detector = pipeline("image-classification", model="prithivMLmods/Deep-Fake-Detector-v2-Model", device=device)

# 5. The Generalist
general_detector = pipeline("image-classification", model="Nahrawy/AIorNot", device=device)

print("Jury Ready. All systems go.")

MAX_IMAGE_DIMENSION = 8000  # pixels — beyond this PIL + models risk running out of memory

# Known AI generation tool names that may appear in an image's EXIF Software tag
AI_SOFTWARE_NAMES = [
    "stable diffusion", "dall-e", "dall·e", "midjourney", "adobe firefly",
    "firefly", "imagen", "comfyui", "automatic1111", "novelai", "invokeai",
    "generative", "ai-generated",
]

# Explicit label maps per model: stripped lowercase label → is_fake bool.
# Prevents misclassification if a model relabels its outputs in a future update.
# The keyword heuristic below is the fallback when a label isn't listed here.
LABEL_MAPS = {
    "face":     {"fake": True, "real": False, "deepfake": True},
    "modern":   {"ai": True, "human": False},
    "legacy":   {"artificial": True, "human": False, "fake": True, "real": False},
    "forensic": {"fake": True, "real": False, "deepfake": True},
    "general":  {"ai": True, "notai": False, "human": False},
}
FAKE_KEYWORDS = ["fake", "ai", "artificial", "generated", "deepfake", "synthetic"]
REAL_KEYWORDS = ["real", "human", "notai", "authentic", "genuine"]


def predict_image(image_path):
    try:
        pil_image = Image.open(image_path).convert("RGB")

        # Reject absurdly large images before model inference to prevent OOM
        width, height = pil_image.size
        if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
            return (
                "Error",
                0.0,
                [f"Image is too large ({width}x{height}px). Maximum is {MAX_IMAGE_DIMENSION}px per side."],
                {},
            )

        reasons = []
        votes_fake = 0.0   # weighted sum — used for verdict threshold
        votes_real = 0.0   # weighted sum — used for ai_probability denominator
        count_fake = 0     # plain count of models that voted fake — used for display
        count_real = 0     # plain count of models that voted real — used for display
        confidences = []   # per-model certainty; failed models are excluded from avg

        # --- STEP 1: JURY VOTING ---

        def cast_vote(model, name, model_key, fake_reason, real_reason):
            nonlocal votes_fake, votes_real, count_fake, count_real
            try:
                res = model(pil_image)
                raw_label = res[0]["label"]
                # Strip whitespace/separators so label maps match reliably
                label = raw_label.lower().replace(" ", "").replace("_", "").replace("-", "")
                conf = res[0]["score"] * 100

                # Try the explicit label map first; fall back to keyword heuristic
                label_map = LABEL_MAPS.get(model_key, {})
                is_fake = label_map.get(label, None)
                if is_fake is None:
                    is_fake = any(x in label for x in FAKE_KEYWORDS)
                    if not any(x in label for x in FAKE_KEYWORDS + REAL_KEYWORDS):
                        # Log unmapped labels so we can update LABEL_MAPS if needed
                        print(f"WARNING: {name} returned unmapped label '{raw_label}' — defaulting to REAL")

                if is_fake and conf > 75:
                    reasons.append(f"❌ {name}: {fake_reason}")
                elif not is_fake and conf > 90:
                    reasons.append(f"✅ {name}: {real_reason}")

                weight = 2.0 if conf > 90.0 else (1.0 if conf >= 75.0 else 0.5)

                if is_fake:
                    votes_fake += weight
                    count_fake += 1
                else:
                    votes_real += weight
                    count_real += 1

                confidences.append(conf)
                return conf
            except Exception as e:
                print(f"Model Error {name}: {e}")
                # Return None — excluded from avg_conf; no vote cast for this model
                return None

        # Ask each expert
        c1 = cast_vote(face_detector,     "Face Check",    "face",     "The eyes or mouth look unnatural.",               "Facial structure looks human and organic.")
        c2 = cast_vote(modern_detector,   "Style Check",   "modern",   "It has the smooth, 'perfect' look of AI art.",    "Lighting looks realistic.")
        c3 = cast_vote(legacy_detector,   "Pattern Check", "legacy",   "Found digital patterns often left by generators.", "Details look random and natural.")
        c4 = cast_vote(forensic_detector, "Pixel Check",   "forensic", "The pixels don't align like a normal photo.",     "Compression looks normal.")
        c5 = cast_vote(general_detector,  "General Check", "general",  "Overall look matches known AI images.",            "Composition feels human.")

        # --- STEP 1b: METADATA SIGNALS ---
        # These supplement model votes without counting toward the N/5 display.

        meta = extract_metadata(image_path)

        # No EXIF → weak fake signal (real camera photos almost always have EXIF)
        if not meta["has_exif"]:
            votes_fake += 0.25
            reasons.append("❌ Metadata Check: No camera data found — AI images rarely have EXIF.")

        # AI tool name in EXIF Software tag → near-certain fake
        software_val = meta.get("software", "Unknown").lower()
        if software_val not in ("unknown", "") and any(kw in software_val for kw in AI_SOFTWARE_NAMES):
            votes_fake += 3.0
            reasons.append(f"❌ Metadata Check: Software tag reads '{meta['software']}' — a known AI generation tool.")

        # Heavy JPEG compression disclaimer (compressed images mimic GAN noise)
        try:
            raw_img = Image.open(image_path)
            if raw_img.format == "JPEG" and hasattr(raw_img, "quantization") and raw_img.quantization:
                luma = raw_img.quantization.get(0, [])
                if luma and (sum(luma) / len(luma)) > 25:
                    reasons.append("⚠️  Compression Check: Image is heavily compressed — result may be less reliable.")
        except Exception as e:
            print(f"JPEG quality check failed: {e}")

        # --- STEP 2: FINAL VERDICT ---

        total_weight = votes_fake + votes_real
        # ai_probability: fraction of weighted evidence that points to fake, as a percent.
        # This is directional (fake vs real), not just jury certainty.
        ai_probability = round((votes_fake / total_weight * 100) if total_weight > 0 else 50.0, 2)

        signals = {
            "Face Expert":     round(c1, 1) if c1 is not None else 0,
            "Artistic Expert": round(c2, 1) if c2 is not None else 0,
            "Legacy Expert":   round(c3, 1) if c3 is not None else 0,
            "Pixel Expert":    round(c4, 1) if c4 is not None else 0,
            "General Expert":  round(c5, 1) if c5 is not None else 0,
        }

        if votes_fake >= 4:
            # count_fake == 5 means all model slots agreed (not the metadata bonus votes)
            score = max(ai_probability, 95.0) if count_fake == 5 else ai_probability
            label = f"AI Generated ({count_fake}/5 Experts Agree)"
        elif votes_fake >= 3:
            label = "Likely AI Generated"
            score = ai_probability
        elif votes_fake >= 2:
            label = "Suspicious / Inconclusive"
            score = ai_probability
        else:
            label = f"Likely Real ({count_real}/5 Experts Agree)"
            score = ai_probability

        return label, score, reasons, signals

    except Exception as e:
        print(f"ERROR: {e}")
        return "Error", 0.0, ["Analysis failed due to server error."], {}


def extract_metadata(image_path):
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
