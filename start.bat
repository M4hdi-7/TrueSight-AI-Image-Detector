@echo off
TITLE TrueSight Launcher
CLS

:: 1. GET LOCAL IP ADDRESS AUTOMATICALLY
:: This looks for your IPv4 address in system settings
FOR /F "tokens=4 delims= " %%a IN ('route print ^| find " 0.0.0.0"') DO (
    IF "%%a" NEQ "0.0.0.0" SET IP=%%a
)

echo ======================================================
echo    TRUESIGHT AI FORENSICS - LAUNCHER
echo ======================================================
echo.
echo [1/2] Starting Backend Server (Port 5000)...
:: Opens a new window, activates venv, runs app.py
start "TrueSight Backend" cmd /k "cd backend && call venv\Scripts\activate && python app.py"

echo [2/2] Starting Frontend Host (Port 8000)...
:: Opens a new window, starts http server
start "TrueSight Frontend" cmd /k "cd frontend && python -m http.server 8000"

echo.
echo ======================================================
echo    SYSTEM READY!
echo ======================================================
echo.
echo    ON YOUR PHONE, OPEN THIS URL:
echo.
echo    http://%IP%:8000
echo.
echo ======================================================
pause