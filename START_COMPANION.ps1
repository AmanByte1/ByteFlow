# ByteFlow Web Companion - PowerShell Startup Script
# Run with: powershell -ExecutionPolicy Bypass -File START_COMPANION.ps1

Write-Host "`n" -ForegroundColor White
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                   ByteFlow Companion                          ║" -ForegroundColor Cyan
Write-Host "║         Intelligent Data Extraction & Lead Generation         ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host "`n"

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python 3.8+ from https://www.python.org" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "`n"

# Create virtual environment if needed
if (-not (Test-Path "venv")) {
    Write-Host "📦 Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    Write-Host "✅ Virtual environment created" -ForegroundColor Green
    Write-Host "`n"
}

# Activate venv
Write-Host "🔌 Activating virtual environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"

# Install requirements
Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt --quiet 2>&1 | Out-Null
Write-Host "✅ Dependencies installed" -ForegroundColor Green
Write-Host "`n"

# Start server
Write-Host "🚀 Starting ByteFlow Companion Server..." -ForegroundColor Green
Write-Host "`n"
Write-Host "📍 Open your browser and go to: " -NoNewline
Write-Host "http://localhost:5000" -ForegroundColor Cyan
Write-Host "`n"
Write-Host "Features:" -ForegroundColor Yellow
Write-Host "  🎯 Lead Generator    - Find local businesses needing your services" -ForegroundColor Gray
Write-Host "  🧠 Intelligence Agent - Extract structured data from any website" -ForegroundColor Gray
Write-Host "  📊 Search & Filter   - Advanced filtering and analysis" -ForegroundColor Gray
Write-Host "  📈 Export Results    - CSV, JSON, and more formats" -ForegroundColor Gray
Write-Host "`n"
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Magenta
Write-Host "`n"

python -m byteflow.web_companion

Read-Host "Press Enter to exit"
