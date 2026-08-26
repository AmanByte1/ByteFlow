@echo off
title ByteFlow Frontend
cd /d "%~dp0"

echo.
echo  ==========================================
set PYTHONPATH=%~dp0
echo   ByteFlow Frontend - Starting...
echo  ==========================================
echo.

pip install fastapi "uvicorn[standard]" httpx qrcode --quiet --exists-action i

set PYTHONPATH=%~dp0
echo Starting ByteFlow Frontend on http://localhost:7860
echo Open on your phone: check the QR code or URL above
echo.
python byteflow_frontend/__main__.py --port 7860 --core-url http://localhost:7861

pause
