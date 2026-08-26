@echo off
title ByteFlow Core API
cd /d "%~dp0"

echo.
echo  ==========================================
echo   ByteFlow Core API - Starting...
echo  ==========================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install from python.org
    pause & exit /b 1
)

:: Install dependencies
echo Installing dependencies...
pip install fastapi "uvicorn[standard]" httpx pydantic psutil --quiet --exists-action i

:: Find best available model
set MODEL=llama3
for /f "tokens=1" %%m in ('ollama list 2^>nul ^| findstr /v "NAME" ^| findstr /v "^$"') do (
    set FIRST_MODEL=%%m
    goto :found
)
:found
if defined FIRST_MODEL (
    set MODEL=%FIRST_MODEL::latest=%
)

echo Using model: %MODEL%
echo.

:: Start core API — run from project folder so imports work
echo Starting ByteFlow Core on http://localhost:7861
echo.
python byteflow/api_server.py --model %MODEL% --port 7861

pause
