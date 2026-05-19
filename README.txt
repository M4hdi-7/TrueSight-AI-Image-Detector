========================================================================
                      TRUESIGHT | AI Image Detector v1.1
========================================================================

Welcome to TrueSight! This is a local web application designed to help detect 
AI-generated and deepfake images.

In version 1.1, TrueSight has been migrated from a local, memory-heavy 
5-model jury system to Hive AI's state-of-the-art AI-Generated & Deepfake 
Content Detection (V3 Playground) API. This transition makes the app extremely 
lightweight, fast, and highly accurate while protecting CPU and RAM resources.

------------------------------------------------------------------------
WHAT IT DOES (Features)
------------------------------------------------------------------------
* Hive AI Classifier: Leverages Hive's advanced deep learning models to 
    predict AI generation probability and deepfake face-swap indicators.
* Explainability: Generates a detailed forensic report explaining exactly 
    WHY the AI reached its verdict (pointing out AI signatures, deepfake 
    risks, and metadata details).
* Metadata Validation: Captures camera make, model, and software EXIF tags 
    to supplement the verdict (e.g., automatically flagging images with 
    "Midjourney" or "stable diffusion" signatures).
* Generator Attribution: Detects and attributes which specific engine 
    generated the image (e.g., Midjourney, DALL-E, Stable Diffusion).
* Smart Memory: Keeps local SQLite database history of all analyzed scans 
    for easy cross-referencing.

------------------------------------------------------------------------
HOW TO INSTALL
------------------------------------------------------------------------
TrueSight v1.1 is extremely fast and lightweight to install since it no longer 
requires heavy machine learning libraries like torch or transformers.

1. Download and unzip this folder.
2. Open the 'backend' folder in your terminal (Command Prompt).
3. Create a virtual environment (recommended):
    python -m venv venv
    venv\Scripts\activate
4. Install the required lightweight libraries:
    pip install -r requirements.txt

------------------------------------------------------------------------
CONFIGURATION
------------------------------------------------------------------------
TrueSight v1.1 requires a Hive API key to analyze images:

1. Create a file named ".env" in the backend/ directory:
    HIVE_API_KEY=your_actual_hive_api_key_here

    (Note: You can copy backend/.env.example to backend/.env and replace 
     the placeholder key)
2. Save your API key in that file. It will be kept completely private 
    locally and is excluded from git commits.

------------------------------------------------------------------------
HOW TO RUN IT
------------------------------------------------------------------------
Use the "One-Click Launcher" to run both the frontend and backend instantly:

1. Double-click the file named "start.bat".
2. Two black terminal windows will open (one for the Flask Backend on port 5000, 
    one for the HTTP Frontend on port 8000).
3. The main terminal window will display the URL to open (e.g., http://192.168.1.5:8000).

------------------------------------------------------------------------
LIMITATIONS & DISCLAIMER
------------------------------------------------------------------------
[!] WARNING [!]
TrueSight is an experimental prototype. The AI models are highly advanced 
but NOT 100% accurate. Do not use this tool as definitive proof of an 
image's authenticity. It is a supplemental forensic tool, and results 
should always be manually reviewed.
========================================================================