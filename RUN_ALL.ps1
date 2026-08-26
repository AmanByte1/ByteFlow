# ByteFlow Full System Launcher (PowerShell)
# Run: Right-click → Run with PowerShell
$Host.UI.RawUI.WindowTitle = "ByteFlow Launcher"
Set-Location $PSScriptRoot

Write-Host ""
Write-Host "  ==========================================" -ForegroundColor Cyan
Write-Host "   ByteFlow Full System Launcher" -ForegroundColor Cyan
Write-Host "  ==========================================" -ForegroundColor Cyan
Write-Host ""

# Find best model
$models = (ollama list 2>$null) -split "`n" |
    Where-Object { $_ -notmatch "NAME|^$" } |
    ForEach-Object { ($_ -split "\s+")[0] -replace ":latest","" } |
    Where-Object { $_ }

$preferred = @("llama3","my-buddy","mistral","phi","gemma")
$model = $null
foreach ($p in $preferred) {
    if ($models -contains $p) { $model = $p; break }
}
if (-not $model -and $models) { $model = $models[0] }
if (-not $model) { $model = "llama3" }

Write-Host "  Model  : $model" -ForegroundColor Green
Write-Host "  Python : $(python --version 2>&1)" -ForegroundColor Green
Write-Host ""

# Install deps
Write-Host "  Installing dependencies..." -ForegroundColor Gray
python -m pip install fastapi "uvicorn[standard]" httpx pydantic qrcode psutil pyperclip --quiet --exists-action i 2>$null

# Start Ollama
Write-Host "  Starting Ollama..." -ForegroundColor Gray
Start-Process "ollama" -ArgumentList "serve" -WindowStyle Minimized -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Start Core API
Write-Host "  Starting ByteFlow Core on :7861..." -ForegroundColor Gray
$core = Start-Process "python" -ArgumentList "byteflow/api_server.py --model $model --port 7861" `
    -WorkingDirectory $PSScriptRoot -PassThru -WindowStyle Normal
Start-Sleep -Seconds 3

# Start Frontend
Write-Host "  Starting ByteFlow Frontend on :7860..." -ForegroundColor Gray
$frontend = Start-Process "python" -ArgumentList "byteflow_frontend/__main__.py --port 7860 --core-url http://localhost:7861" `
    -WorkingDirectory $PSScriptRoot -PassThru -WindowStyle Normal

Write-Host ""
Write-Host "  ==========================================" -ForegroundColor Green
Write-Host "   ByteFlow is running!" -ForegroundColor Green
Write-Host ""
Write-Host "   Core API  : http://localhost:7861" -ForegroundColor Cyan
Write-Host "   Phone UI  : http://localhost:7860" -ForegroundColor Cyan
Write-Host "   API Docs  : http://localhost:7861/docs" -ForegroundColor Cyan
Write-Host "   Aether    : open aether_village.html in Chrome" -ForegroundColor Yellow
Write-Host ""
Write-Host "   Press Enter to STOP everything" -ForegroundColor Gray
Write-Host "  ==========================================" -ForegroundColor Green
Read-Host

# Cleanup
Stop-Process -Id $core.Id -Force -ErrorAction SilentlyContinue
Stop-Process -Id $frontend.Id -Force -ErrorAction SilentlyContinue
Write-Host "  Stopped. Goodbye!" -ForegroundColor Gray
