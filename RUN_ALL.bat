@echo off
title ByteFlow - Full Launch
cd /d "%~dp0"

echo.
echo  ==========================================
echo   ByteFlow - Full System Launch
echo  ==========================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (echo ERROR: Python not found & pause & exit /b 1)

:: Check Ollama
ollama --version >nul 2>&1
if errorlevel 1 (echo ERROR: Ollama not found. Install from ollama.com & pause & exit /b 1)

:: Install all dependencies once
echo [1/4] Installing Python dependencies...
pip install fastapi "uvicorn[standard]" httpx pydantic qrcode psutil pyperclip --quiet --exists-action i

:: Find best model
set MODEL=llama3
echo [2/4] Checking Ollama models...
for /f "tokens=1" %%m in ('ollama list 2^>nul ^| findstr /v "NAME" ^| findstr /v "^$"') do (
    set RAW=%%m
    set MODEL=!RAW::latest=!
    goto :model_found
)
:model_found
echo     Using model: %MODEL%

:: Start ollama serve in background
echo [3/4] Starting Ollama...
start /min "" ollama serve
timeout /t 2 /nobreak >nul

:: Start ByteFlow Core in new window
echo [4/4] Starting ByteFlow Core (port 7861)...
start "ByteFlow Core" cmd /k "cd /d %~dp0 && set PYTHONPATH=%~dp0 && python byteflow/api_server.py --model %MODEL% --port 7861"
timeout /t 4 /nobreak >nul

:: Start Frontend in new window
echo     Starting ByteFlow Frontend (port 7860)...
start "ByteFlow Frontend" cmd /k "cd /d %~dp0 && set PYTHONPATH=%~dp0 && python byteflow_frontend/__main__.py --port 7860 --core-url http://localhost:7861"

echo.
echo  ==========================================
echo   ByteFlow is starting up!
echo.
echo   Core API : http://localhost:7861
echo   Phone UI : http://localhost:7860
echo   API Docs : http://localhost:7861/docs
echo.
echo   Close the two new windows to stop ByteFlow
echo  ==========================================
echo.
pause
