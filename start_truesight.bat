@echo off
TITLE TrueSight Netlify Launcher
CLS

echo ======================================================
echo    TRUESIGHT AI FORENSICS - ONLINE LAUNCHER
echo ======================================================
echo.
echo [1/2] Starting Backend Server (Port 5000)...
:: Opens a new window, activates venv, runs app.py
start "TrueSight Backend" cmd /k "cd backend && call venv\Scripts\activate && python app.py"

echo [2/2] Starting Ngrok Tunnel...
:: Opens a new window, starts ngrok with the static domain
start "Ngrok Tunnel" cmd /k "ngrok http --domain=phony-worry-these.ngrok-free.dev 5000"

echo.
echo ======================================================
echo    SYSTEM READY!
echo ======================================================
echo.
echo    Your backend is now live on your permanent domain.
echo    You can open your Netlify link on any device!
echo.
echo ======================================================
pause
