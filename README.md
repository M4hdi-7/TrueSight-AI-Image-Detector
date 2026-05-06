# TrueSight | AI Image Detector

Welcome to TrueSight! This is a local web application designed to help detect AI-generated images.

Unlike simple detectors that guess "Real" or "Fake," TrueSight uses a "Jury System." It runs 5 different AI models simultaneously to vote on an image, and then applies some smart logic (checking for metadata, weird resolutions, etc.) to give you a final, honest verdict.

## Features
* **The Jury System:** 5 AI brains work together. If they disagree, the app tells you.
* **Explainability:** It doesn't just give you a percentage. It generates a detailed forensic report explaining exactly WHY the AI thinks the image is real or fake (e.g., pointing out unnatural pixels or suspicious metadata).
* **Cross-Device:** Run it on your PC, but use it from your phone’s browser.
* **Smart Memory:** It saves a history of every scan you do (on your PC), so you can look back at results later.
* **Honest Scoring:** It uses nuanced categories like "Likely Real," "Suspicious / Inconclusive," and "AI Generated" depending on how many models agree.

## How to Install
You need Python installed on your computer.

1. Download and unzip this folder.
2. Open the `backend` folder in your terminal (Command Prompt).
3. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```
4. Install the required libraries automatically:
   ```bash
   pip install -r requirements.txt
   ```
   *(Note: This might take a few minutes as it downloads the AI tools)*

## How to Run It
The easiest way is to use the "One-Click Launcher":

1. Double-click the file named `start.bat`.
2. Two black windows will open (one for the Brain, one for the Website).
3. The main window will tell you exactly what URL to type on your phone (e.g., `http://192.168.1.5:8000`).

**Manual Method:**
If the bat file doesn't work, just run `python app.py` in the backend folder and `python -m http.server 8000` in the frontend folder.

## Using it on Your Phone
Make sure your phone is connected to the same Wi-Fi as your computer.
Type the IP address shown in the launcher into your phone's browser (Chrome/Safari).

*Tip: If you scan an image on your PC and want to see it on your phone, go to the History tab and tap the blue "Refresh" button.*

## Limitations
* **WhatsApp/Social Media Images:** These are heavily compressed. The app might label them as "Uncertain" or "Suspicious" because the compression artifacts look a bit like AI noise. This is normal behavior for v1.0.
* **Speed:** Since it runs 5 heavy AI models on your own computer, the first scan might take a few seconds depending on your PC's speed.

## Tech Stack
Built with Python (Flask), PyTorch, Hugging Face Transformers, and vanilla JavaScript/HTML/CSS. Data is stored locally in a SQLite database.
