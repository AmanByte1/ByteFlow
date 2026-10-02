@echo off
setlocal enabledelayedexpansion

REM ByteFlow Companion - Accelerated Edition Launcher
REM ================================================

echo.
echo ============================================================
echo   ByteFlow Companion - Accelerated Edition ⚡
echo ============================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found! Please install Python 3.8+
    pause
    exit /b 1
)

echo ✅ Python found: 
python --version
echo.

REM Check if Flask is installed
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo ⚠️ Flask not found. Installing...
    pip install flask flask-cors flask-limiter
    if errorlevel 1 (
        echo ❌ Failed to install Flask
        pause
        exit /b 1
    )
    echo ✅ Flask installed
)

REM Check if LocalAI Accelerator is available
python -c "from local_ai_accelerator import ByteFlowAcceleratorPipeline" >nul 2>&1
if errorlevel 1 (
    echo.
    echo ⚠️ LocalAI Accelerator not found
    echo.
    echo Options:
    echo 1. Install it: pip install local-ai-accelerator
    echo 2. Build locally: cd LocalAI-Accelerator ^&^& pip install -e .
    echo.
    echo The companion will still work in standard mode (slower).
    echo.
) else (
    echo ✅ LocalAI Accelerator found - 5.2x SPEEDUP ENABLED!
)

echo.
echo ============================================================
echo Starting Companion Server...
echo ============================================================
echo.
echo 🚀 Server starting on http://localhost:5000
echo 📱 Open this URL in your browser
echo ⏹️  Press Ctrl+C to stop
echo.
echo ============================================================
echo.

REM Run the accelerated companion
if exist "byteflow\web_companion_accelerated.py" (
    echo 📂 Found: byteflow/web_companion_accelerated.py
    python byteflow/web_companion_accelerated.py
) else if exist "web_companion_accelerated.py" (
    echo 📂 Found: web_companion_accelerated.py
    python web_companion_accelerated.py
) else (
    echo ❌ web_companion_accelerated.py not found!
    echo.
    echo Make sure you're in the ByteFlow directory with:
    echo   - web_companion_accelerated.py
    echo   OR
    echo   - byteflow/web_companion_accelerated.py
    echo.
    pause
    exit /b 1
)

pause
