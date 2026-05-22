import os
import sys
from dotenv import load_dotenv

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
sys.path.insert(0, BACKEND_DIR)

from ai_model.model import predict_image


def _safe_print(reasons):
    return [r.encode('ascii', errors='replace').decode('ascii') for r in reasons]


def main():
    print("--- TRUESIGHT SIGHTENGINE INTEGRATION VERIFIER ---")

    test_image_missing_key = os.path.join(PROJECT_ROOT, "Test", "images.jpg")
    test_image_full = os.path.join(PROJECT_ROOT, "Test", "Dwayne_Johnson_2014_(cropped).jpg")

    # 1. Test Behavior WITHOUT Sightengine credentials
    print("\n[Test 1] Testing without SIGHTENGINE_API_USER / SIGHTENGINE_API_SECRET in environment...")
    old_user = os.environ.pop("SIGHTENGINE_API_USER", None)
    old_secret = os.environ.pop("SIGHTENGINE_API_SECRET", None)
    try:
        label, score, reasons, signals, metadata = predict_image(test_image_missing_key)
        print(f"Verdict: {label}")
        print(f"Score: {score}")
        print(f"Reasons: {_safe_print(reasons)}")
        print(f"Signals: {signals}")
        print(f"Metadata: {metadata}")
        assert label == "Error"
        print("PASS: Handled missing API credentials gracefully.")
    except Exception as e:
        print(f"FAIL: Unhandled exception when credentials missing: {e}")

    if old_user:
        os.environ["SIGHTENGINE_API_USER"] = old_user
    if old_secret:
        os.environ["SIGHTENGINE_API_SECRET"] = old_secret

    # 2. Test Behavior WITH Sightengine credentials
    load_dotenv()
    user = os.environ.get("SIGHTENGINE_API_USER")
    secret = os.environ.get("SIGHTENGINE_API_SECRET")
    if not user or not secret or user == "your_sightengine_api_user_here":
        print("\n[Notice] Skipping API execution test: Sightengine credentials not configured in backend/.env")
        return

    print("\n[Test 2] Testing WITH Sightengine credentials...")
    print(f"Analyzing {test_image_full}...")
    try:
        label, score, reasons, signals, metadata = predict_image(test_image_full)
        print(f"Verdict: {label}")
        print(f"Score: {score}")
        print(f"Reasons: {_safe_print(reasons)}")
        print(f"Signals: {signals}")
        print(f"Metadata: {metadata}")
        print("PASS: Successfully classified image.")
    except Exception as e:
        print(f"FAIL: API execution failed with error: {e}")


if __name__ == "__main__":
    main()
