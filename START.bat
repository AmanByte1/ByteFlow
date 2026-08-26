@echo off
setlocal EnableDelayedExpansion
title ByteFlow Launcher
color 0A
cd /d "%~dp0"

echo.
echo  ==========================================
echo   ByteFlow - Starting up...
echo  ==========================================
echo.

:: ── Check Python ──────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Install from python.org
    pause & exit /b 1
)

:: ── Check Ollama ──────────────────────────────────────────
ollama --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Ollama not found. Install from ollama.com
    pause & exit /b 1
)

:: ── Find best available model ──────────────────────────────
echo  Checking Ollama models...
set MODEL=llama3
for /f "tokens=1" %%m in ('ollama list 2^>nul ^| findstr /v "NAME" ^| findstr /v "^$"') do (
    set RAW=%%m
    set MODEL=!RAW::latest=!
    goto :model_found
)
:model_found
echo  Using model: %MODEL%
echo.

:: ── Install dependencies ───────────────────────────────────
echo  Checking dependencies...
pip install fastapi "uvicorn[standard]" httpx pydantic qrcode psutil pyperclip --quiet --exists-action i 2>nul

:: ── Start Ollama serve (silent, ignore if already running) ─
start /min "" ollama serve 2>nul
timeout /t 2 /nobreak >nul

:: ── Start ByteFlow Core in a new window ───────────────────
echo  Starting ByteFlow Core (port 7861)...
start "ByteFlow Core" cmd /k "cd /d %~dp0 && python byteflow/api_server.py --model %MODEL% --port 7861"
timeout /t 4 /nobreak >nul

:: ── Start Frontend — one command, correct args ────────────
echo  Starting ByteFlow Frontend (port 7860)...
echo.
echo  ==========================================
echo   Open on your PHONE:
echo   Scan QR or visit URL shown below
echo  ==========================================
echo.

python byteflow_frontend/__main__.py --port 7860 --core-url http://localhost:7861

pause
