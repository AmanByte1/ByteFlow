@echo off
REM Lead Generation Companion Startup Script
REM Windows Batch File

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║   Lead Generation Companion - ByteFlow                     ║
echo ║   Find & qualify businesses that need your services        ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Python not found
    echo Please install Python 3.8+ and add it to PATH
    pause
    exit /b 1
)

REM Check if requirements are installed
echo 📦 Checking dependencies...
pip show crawl4ai >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Installing required packages...
    pip install -r requirements_lead_generation.txt
)

REM Start the companion
echo.
echo 🚀 Starting Lead Generation Companion...
echo.
python -m byteflow.lead_generation_companion

pause
