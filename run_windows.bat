@echo off
echo ===================================================
echo Active Tremor Cancellation System - Startup Script
echo ===================================================

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to PATH.
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b
)

:: Create Virtual Environment if it doesn't exist
if not exist "venv" (
    echo [INFO] Creating a local Python Virtual Environment (venv)...
    python -m venv venv
)

:: Activate Virtual Environment
echo [INFO] Activating Virtual Environment...
call venv\Scripts\activate

:: Install Dependencies quietly
echo [INFO] Checking and installing dependencies from requirements.txt...
pip install -r requirements.txt

:: Run the Dashboard
echo [INFO] Starting Dashboard...
python python_src\main.py

:: Keep command prompt open if the app crashes so you can read the error
pause
