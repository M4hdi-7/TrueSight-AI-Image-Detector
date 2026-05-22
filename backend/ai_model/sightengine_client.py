import os
import requests

SIGHTENGINE_API_URL = "https://api.sightengine.com/1.0/check.json"
TIMEOUT_SECONDS = 60


def classify_image(image_path: str) -> dict:
    """
    POSTs the image to Sightengine's AI-Generated Image Detection API.
    Uses the 'genai' model. Returns the parsed JSON response.
    """
    api_user = os.environ.get("SIGHTENGINE_API_USER")
    api_secret = os.environ.get("SIGHTENGINE_API_SECRET")
    if not api_user or not api_secret:
        raise RuntimeError(
            "SIGHTENGINE_API_USER / SIGHTENGINE_API_SECRET not found in environment variables. "
            "Please check your .env file."
        )

    with open(image_path, "rb") as f:
        data = {
            "models": "genai",
            "api_user": api_user,
            "api_secret": api_secret,
        }
        files = {"media": f}
        response = requests.post(
            SIGHTENGINE_API_URL,
            data=data,
            files=files,
            timeout=TIMEOUT_SECONDS,
        )

    response.raise_for_status()
    return response.json()
