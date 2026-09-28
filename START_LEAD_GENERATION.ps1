# Lead Generation Companion Startup Script
# PowerShell Version for Windows

Write-Host "`n╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   Lead Generation Companion - ByteFlow                     ║" -ForegroundColor Cyan
Write-Host "║   Find & qualify businesses that need your services        ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

# Check if Python is installed
$python_check = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Error: Python not found" -ForegroundColor Red
    Write-Host "Please install Python 3.8+ and add it to PATH" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "✅ Python found: $python_check" -ForegroundColor Green

# Check dependencies
Write-Host "`n📦 Checking dependencies..." -ForegroundColor Yellow
$pip_check = pip show crawl4ai 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Installing required packages..." -ForegroundColor Yellow
    pip install -r requirements_lead_generation.txt
}

# Start the companion
Write-Host "`n🚀 Starting Lead Generation Companion...`n" -ForegroundColor Green
python -m byteflow.lead_generation_companion

Read-Host "Press Enter to exit"
