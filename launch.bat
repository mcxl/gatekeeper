@echo off
title Simple SWMS — Launching...
echo.
echo  ================================
echo   SIMPLE SWMS
echo   Starting development server...
echo  ================================
echo.

:: Change to the gatekeeper project directory
cd /d "%~dp0"

:: Check if venv exists
if not exist "venv\Scripts\activate.bat" (
    echo  ERROR: Virtual environment not found.
    echo  Run setup first: python -m venv venv
    echo  Then: venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

:: Activate virtual environment
call venv\Scripts\activate.bat

:: Check if uvicorn is available
where uvicorn >nul 2>&1
if %errorlevel% neq 0 (
    echo  ERROR: uvicorn not found in virtual environment.
    echo  Run: pip install uvicorn
    pause
    exit /b 1
)

echo  Starting FastAPI backend on http://localhost:8000
echo  Press Ctrl+C in this window to stop the server.
echo.

:: Open dev.html in Chrome after 3 second delay
:: Uses PowerShell to wait then open browser
powershell -Command "Start-Sleep 3; Start-Process 'http://localhost:8000/docs'"

:: Also open the dev UI directly
powershell -Command "Start-Sleep 3; Start-Process (Resolve-Path 'frontend\dev.html').Path"

:: Start the FastAPI server (this keeps the window open)
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

:: If server stops
echo.
echo  Server stopped.
pause
