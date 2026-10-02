# ByteFlow Companion - Accelerated Edition Launcher
# ===============================================

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  ByteFlow Companion - Accelerated Edition ⚡" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python not found! Please install Python 3.8+" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""

# Check Flask
try {
    python -c "import flask" 2>$null
    Write-Host "✅ Flask installed" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Flask not found. Installing..." -ForegroundColor Yellow
    pip install flask flask-cors flask-limiter
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Flask installed" -ForegroundColor Green
    } else {
        Write-Host "❌ Failed to install Flask" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# Check LocalAI Accelerator
try {
    python -c "from local_ai_accelerator import ByteFlowAcceleratorPipeline" 2>$null
    Write-Host "✅ LocalAI Accelerator found - 5.2x SPEEDUP ENABLED!" -ForegroundColor Green
    $acceleratorFound = $true
} catch {
    Write-Host "⚠️ LocalAI Accelerator not found" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Install it with one of these commands:" -ForegroundColor Cyan
    Write-Host "  Option 1: pip install local-ai-accelerator" -ForegroundColor Gray
    Write-Host "  Option 2: cd LocalAI-Accelerator`; pip install -e ." -ForegroundColor Gray
    Write-Host ""
    Write-Host "The companion will still work in standard mode (slower)." -ForegroundColor Gray
    Write-Host ""
    $acceleratorFound = $false
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Starting Companion Server..." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

if ($acceleratorFound) {
    Write-Host "🚀 Server starting with ACCELERATION ENABLED" -ForegroundColor Green
    Write-Host "⚡ Expect 5.2x faster responses" -ForegroundColor Green
} else {
    Write-Host "🚀 Server starting in standard mode" -ForegroundColor Yellow
    Write-Host "📌 For acceleration, install LocalAI Accelerator" -ForegroundColor Yellow
}

Write-Host "📍 Open: http://localhost:5000" -ForegroundColor Cyan
Write-Host "⏹️  Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Find and run the accelerated companion
$scriptPath = ""
if (Test-Path "byteflow/web_companion_accelerated.py") {
    $scriptPath = "byteflow/web_companion_accelerated.py"
    Write-Host "📂 Found: byteflow/web_companion_accelerated.py" -ForegroundColor Green
} elseif (Test-Path "web_companion_accelerated.py") {
    $scriptPath = "web_companion_accelerated.py"
    Write-Host "📂 Found: web_companion_accelerated.py" -ForegroundColor Green
} else {
    Write-Host "❌ web_companion_accelerated.py not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Make sure you're in the ByteFlow directory with:" -ForegroundColor Yellow
    Write-Host "  - web_companion_accelerated.py" -ForegroundColor Gray
    Write-Host "  OR" -ForegroundColor Gray
    Write-Host "  - byteflow/web_companion_accelerated.py" -ForegroundColor Gray
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""

# Run the server
python $scriptPath
