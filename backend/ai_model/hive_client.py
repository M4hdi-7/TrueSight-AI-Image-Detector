import os
import requests

HIVE_API_URL = "https://api.thehive.ai/api/v3/hive/ai-generated-and-deepfake-content-detection"
TIMEOUT_SECONDS = 60

def classify_image(image_path: str) -> dict:
    """
    POSTs the image to Hive's AI-Generated and Deepfake Content Detection V3 Playground API.
    Uses multipart/form-data with the parameter 'media'.
    Returns the parsed JSON response.
    """
    hive_api_key = os.environ.get("HIVE_API_KEY")
    if not hive_api_key:
        raise RuntimeError("HIVE_API_KEY not found in environment variables. Please check your .env file.")
        
    with open(image_path, "rb") as f:
        headers = {
            "Authorization": f"Bearer {hive_api_key}"
        }
        # Using requests' files parameter automatically sets Content-Type to multipart/form-data
        # with the correct boundary values.
        files = {
            "media": f
        }
        response = requests.post(
            HIVE_API_URL,
            headers=headers,
            files=files,
            timeout=TIMEOUT_SECONDS
        )
        
    response.raise_for_status()
    return response.json()
