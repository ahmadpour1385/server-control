@echo off
title Server Control
cd /d "%~dp0"
set PORT=8000

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] venv not found. Create it first:
    echo     python -m venv venv
    echo     venv\Scripts\activate
    echo     pip install -r requirements.txt
    pause
    exit /b 1
)

REM Optional: start SSH inside WSL (for the test server). Remove REM to enable.
REM wsl -u root service ssh start

echo Starting Server Control on http://127.0.0.1:%PORT%/
echo Close this window (or press Ctrl+C) to stop the panel.
start "" powershell -WindowStyle Hidden -Command "Start-Sleep 3; Start-Process 'http://127.0.0.1:%PORT%/'"

venv\Scripts\python.exe manage.py runserver 127.0.0.1:%PORT% --noreload

echo.
echo Server stopped.
pause