@echo off
title ByteFlow Installer
cd /d "%~dp0"
color 0A

echo.
echo  ==========================================
echo   ByteFlow - Installing...
echo  ==========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Install from python.org
    pause & exit /b 1
)

echo  Installing ByteFlow as a system command...
echo  (This makes "byteflow companion" work from anywhere)
echo.

pip install -e . --quiet
if errorlevel 1 (
    echo  [ERROR] Install failed. Try running as Administrator.
    pause & exit /b 1
)

pip install click ollama fastapi "uvicorn[standard]" httpx pydantic qrcode psutil pyperclip --quiet --exists-action i

echo.
echo  ==========================================
echo   Installation complete!
echo.
echo   You can now run from ANYWHERE:
echo     byteflow companion
echo     byteflow companion --model q1
echo     byteflow companion --voice
echo     byteflow run "show system info"
echo     byteflow chat "hello"
echo.
echo   Model aliases:
echo     q1  = qwen2.5-coder:1.5b
echo     l3  = llama3
echo     mb  = my-buddy
echo     m   = mistral
echo  ==========================================
echo.
pause
