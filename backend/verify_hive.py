import os
import sys
from dotenv import load_dotenv

# Make `ai_model` importable no matter which directory this script is launched from.
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
sys.path.insert(0, BACKEND_DIR)

from ai_model.model import predict_image


def _safe_print(reasons):
    """Strip non-ASCII so terminals on Windows don't choke on the emoji prefixes."""
    return [r.encode('ascii', errors='replace').decode('ascii') for r in reasons]


def main():
    print("--- TRUESIGHT HIVE INTEGRATION VERIFIER ---")

    test_image_missing_key = os.path.join(PROJECT_ROOT, "Test", "images.jpg")
    test_image_full = os.path.join(PROJECT_ROOT, "Test", "Dwayne_Johnson_2014_(cropped).jpg")

    # 1. Test Behavior WITHOUT HIVE_API_KEY
    print("\n[Test 1] Testing without HIVE_API_KEY in environment...")
    old_key = os.environ.pop("HIVE_API_KEY", None)
    try:
        label, score, reasons, signals, metadata = predict_image(test_image_missing_key)
        print(f"Verdict: {label}")
        print(f"Score: {score}")
        print(f"Reasons: {_safe_print(reasons)}")
        print(f"Signals: {signals}")
        print(f"Metadata: {metadata}")
        assert label == "Error"
        assert "API key" in reasons[0]
        print("PASS: Handled missing API key gracefully.")
    except Exception as e:
        print(f"FAIL: Unhandled exception when API key missing: {e}")

    # Restore key for next test
    if old_key:
        os.environ["HIVE_API_KEY"] = old_key

    # 2. Test Behavior WITH HIVE_API_KEY
    load_dotenv()
    key = os.environ.get("HIVE_API_KEY")
    if not key or key == "your_hive_api_key_here":
        print("\n[Notice] Skipping API execution test: HIVE_API_KEY not configured in backend/.env")
        return

    print("\n[Test 2] Testing WITH HIVE_API_KEY...")
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
