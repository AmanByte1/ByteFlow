@echo off
REM ═════════════════════════════════════════════════════════════════════
REM ByteFlow Web Companion - Windows Startup Script
REM ═════════════════════════════════════════════════════════════════════

cls
echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                   ByteFlow Companion                          ║
echo ║         Intelligent Data Extraction & Lead Generation         ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org
    pause
    exit /b 1
)

echo ✅ Python found
echo.

REM Check if venv exists
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ Failed to create virtual environment
        pause
        exit /b 1
    )
    echo ✅ Virtual environment created
    echo.
)

REM Activate venv
call venv\Scripts\activate.bat

REM Install/update requirements
echo 📦 Installing dependencies...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ⚠️ Some dependencies may not have installed correctly
)
echo ✅ Dependencies installed
echo.

REM Start the server
echo 🚀 Starting ByteFlow Companion Server...
echo.
echo 📍 Open your browser and go to: http://localhost:5000
echo.
echo Features:
echo   🎯 Lead Generator    - Find local businesses needing your services
echo   🧠 Intelligence Agent - Extract structured data from any website
echo   📊 Search & Filter   - Advanced filtering and analysis
echo   📈 Export Results    - CSV, JSON, and more formats
echo.
echo Press Ctrl+C to stop the server
echo.

python -m byteflow.web_companion

pause
