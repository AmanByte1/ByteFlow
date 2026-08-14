@echo off
title ByteFlow Launcher
color 0A

echo.
echo  ==========================================
echo   ByteFlow - Starting up...
echo  ==========================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Install from python.org
    pause
    exit /b 1
)

:: Check Ollama
ollama --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Ollama not found. Install from ollama.com
    pause
    exit /b 1
)

:: Check what models are available
echo  Checking Ollama models...
for /f "tokens=1" %%m in ('ollama list 2^>nul ^| findstr /v "NAME" ^| findstr /v "^$"') do (
    set MODEL=%%m
    goto :found_model
)
echo  [ERROR] No Ollama models found. Run: ollama pull llama3
pause
exit /b 1

:found_model
:: Strip :latest from model name
set MODEL=%MODEL::latest=%
echo  Using model: %MODEL%
echo.

:: Install dependencies silently
echo  Checking dependencies...
pip install fastapi "uvicorn[standard]" httpx pydantic qrcode psutil pyperclip --quiet --exists-action i

:: Start Ollama serve in background (ignore if already running)
start /min "" ollama serve

:: Wait a moment for ollama to be ready
timeout /t 2 /nobreak >nul

:: Start ByteFlow core in background
echo  Starting ByteFlow Core (port 7861)...
start /min "ByteFlow Core" cmd /c "python -m byteflow.api_server --port 7861 --model %MODEL% 2>&1 | tee byteflow_core.log"

:: Wait for core to be ready
timeout /t 3 /nobreak >nul

:: Start frontend
echo  Starting ByteFlow Frontend (port 7860)...
echo.
echo  ==========================================
echo   Open on your PHONE:
echo   (URL will appear below)
echo  ==========================================
echo.

python -m byteflow_frontend --port 7860 --core-port 7861

pause
