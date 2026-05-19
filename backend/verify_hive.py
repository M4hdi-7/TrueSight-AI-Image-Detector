import os
import sys
from dotenv import load_dotenv

# Ensure the backend directory is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_model.model import predict_image

def main():
    print("--- TRUESIGHT HIVE INTEGRATION VERIFIER ---")
    
    # 1. Test Behavior WITHOUT HIVE_API_KEY
    print("\n[Test 1] Testing without HIVE_API_KEY in environment...")
    old_key = os.environ.pop("HIVE_API_KEY", None)
    try:
        label, score, reasons, signals = predict_image("Test/images.jpg")
        print(f"Verdict: {label}")
        print(f"Score: {score}")
        safe_reasons = [r.encode('ascii', errors='replace').decode('ascii') for r in reasons]
        print(f"Reasons: {safe_reasons}")
        print(f"Signals: {signals}")
        assert label == "Error"
        assert "API key" in reasons[0]
        print("PASS: Handled missing API key gracefully.")
    except Exception as e:
        print(f"FAIL: Unhandled exception when API key missing: {e}")
        
    # Put key back if it existed
    if old_key:
        os.environ["HIVE_API_KEY"] = old_key
        
    # 2. Test Behavior WITH HIVE_API_KEY
    load_dotenv()
    key = os.environ.get("HIVE_API_KEY")
    if not key or key == "your_hive_api_key_here":
        print("\n[Notice] Skipping API execution test: HIVE_API_KEY not configured in backend/.env")
        return
        
    print("\n[Test 2] Testing WITH HIVE_API_KEY...")
    # Let's test on a real image from the Test folder
    image_path = "Test/Dwayne_Johnson_2014_(cropped).jpg"
    print(f"Analyzing {image_path}...")
    try:
        label, score, reasons, signals = predict_image(image_path)
        print(f"Verdict: {label}")
        print(f"Score: {score}")
        safe_reasons = [r.encode('ascii', errors='replace').decode('ascii') for r in reasons]
        print(f"Reasons: {safe_reasons}")
        print(f"Signals: {signals}")
        print("PASS: Successfully classified image.")
    except Exception as e:
        print(f"FAIL: API execution failed with error: {e}")

if __name__ == "__main__":
    main()
