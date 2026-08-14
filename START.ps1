# ByteFlow PowerShell Launcher
# Run with: .\START.ps1

$Host.UI.RawUI.WindowTitle = "ByteFlow"
$ErrorActionPreference = "Stop"

function Write-Header {
    Write-Host ""
    Write-Host "  ==========================================" -ForegroundColor Cyan
    Write-Host "   ByteFlow v2.0  -  AI Desktop Assistant" -ForegroundColor Cyan
    Write-Host "  ==========================================" -ForegroundColor Cyan
    Write-Host ""
}

function Check-Command($cmd) {
    $null = Get-Command $cmd -ErrorAction SilentlyContinue
    return $?
}

Write-Header

# ── Check Python ──────────────────────────────────────────────────────────────
if (-not (Check-Command "python")) {
    Write-Host "  [ERROR] Python not found." -ForegroundColor Red
    Write-Host "  Install from: https://python.org" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}
$pyver = python --version 2>&1
Write-Host "  Python : $pyver" -ForegroundColor Green

# ── Check Ollama ──────────────────────────────────────────────────────────────
if (-not (Check-Command "ollama")) {
    Write-Host "  [ERROR] Ollama not found." -ForegroundColor Red
    Write-Host "  Install from: https://ollama.com" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# ── Find best available model ─────────────────────────────────────────────────
Write-Host "  Checking Ollama models..." -ForegroundColor Gray
$models = ollama list 2>$null | Select-String -Pattern "^\S+" | ForEach-Object {
    ($_.Matches.Value -replace ":latest", "")
} | Where-Object { $_ -ne "NAME" -and $_ -ne "" }

if (-not $models) {
    Write-Host "  [ERROR] No Ollama models installed." -ForegroundColor Red
    Write-Host "  Run: ollama pull llama3" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Prefer llama3, then my-buddy, then first available
$preferred = @("llama3", "my-buddy", "mistral", "phi", "gemma")
$model = $null
foreach ($p in $preferred) {
    if ($models -contains $p) { $model = $p; break }
}
if (-not $model) { $model = $models[0] }

Write-Host "  Model  : $model" -ForegroundColor Green
Write-Host "  Models : $($models -join ', ')" -ForegroundColor Gray
Write-Host ""

# ── Install Python dependencies ───────────────────────────────────────────────
Write-Host "  Installing/checking dependencies..." -ForegroundColor Gray
python -m pip install fastapi "uvicorn[standard]" httpx pydantic qrcode psutil pyperclip --quiet --exists-action i 2>$null
Write-Host "  Dependencies OK" -ForegroundColor Green
Write-Host ""

# ── Start Ollama serve (if not already running) ───────────────────────────────
$ollamaRunning = $false
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 2 -ErrorAction Stop
    $ollamaRunning = $true
    Write-Host "  Ollama : already running" -ForegroundColor Green
} catch {
    Write-Host "  Starting Ollama..." -ForegroundColor Gray
    Start-Process "ollama" -ArgumentList "serve" -WindowStyle Minimized
    Start-Sleep -Seconds 3
    Write-Host "  Ollama : started" -ForegroundColor Green
}

# ── Start ByteFlow Core ───────────────────────────────────────────────────────
Write-Host "  Starting ByteFlow Core (port 7861)..." -ForegroundColor Gray
$core = Start-Process "python" -ArgumentList "-m byteflow.api_server --port 7861 --model $model" `
    -WindowStyle Minimized -PassThru
Start-Sleep -Seconds 3

# Verify core is up
try {
    $ping = Invoke-WebRequest -Uri "http://localhost:7861/health" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  Core   : online (PID $($core.Id))" -ForegroundColor Green
} catch {
    Write-Host "  Core   : starting (may take a moment)" -ForegroundColor Yellow
}

# ── Start Frontend ────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  ==========================================" -ForegroundColor Cyan
Write-Host "   Opening ByteFlow Frontend..." -ForegroundColor Cyan
Write-Host "   Scan the QR code with your phone!" -ForegroundColor Yellow
Write-Host "  ==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Press Ctrl+C to stop ByteFlow" -ForegroundColor Gray
Write-Host ""

try {
    python -m byteflow_frontend --port 7860 --core-port 7861
} finally {
    # Cleanup on exit
    Write-Host ""
    Write-Host "  Stopping ByteFlow..." -ForegroundColor Gray
    Stop-Process -Id $core.Id -Force -ErrorAction SilentlyContinue
    Write-Host "  Stopped. Goodbye!" -ForegroundColor Gray
}
