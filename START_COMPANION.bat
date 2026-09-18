@echo off
setlocal EnableDelayedExpansion
title ByteFlow Companion
color 0A
cd /d "%~dp0"

echo.
echo  ==========================================
echo   ByteFlow Companion v3
echo  ==========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (echo  [ERROR] Python not found & pause & exit /b 1)
ollama --version >nul 2>&1
if errorlevel 1 (echo  [ERROR] Ollama not found & pause & exit /b 1)

echo  Finding best model...
set MODEL=llama3
for /f "tokens=1" %%m in ('ollama list 2^>nul ^| findstr /v "NAME" ^| findstr /v "^$"') do (
    set RAW=%%m
    set MODEL=!RAW::latest=!
    goto :found
)
:found
echo  Model: %MODEL%
echo.

pip install psutil pyperclip --quiet --exists-action i 2>nul

set PYTHONPATH=%~dp0

start /min "" ollama serve 2>nul
timeout /t 2 /nobreak >nul

echo  Launching companion...
echo  (Holographic orb will appear on screen)
echo  Right-click orb to quit.
echo.
echo  Model aliases you can say or type:
echo    q1     = qwen2.5-coder:1.5b
echo    l3     = llama3
echo    mb     = my-buddy
echo    m      = mistral
echo    cl     = codellama
echo.

python byteflow/companion.py --model %MODEL%
pause
