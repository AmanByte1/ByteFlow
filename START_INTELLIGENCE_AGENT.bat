@echo off
REM Intelligence Agent Startup Script
REM Windows Batch File

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║   Intelligence Agent - ByteFlow                           ║
echo ║   Smart Web Data Extraction with LLM Refinement          ║
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

REM Start the agent
echo.
echo 🚀 Starting Intelligence Agent...
echo.
python -m byteflow.intelligence_companion

pause
