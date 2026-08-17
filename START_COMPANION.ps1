# ByteFlow Full Companion Launcher
$Host.UI.RawUI.WindowTitle = "ByteFlow Companion"

Write-Host ""
Write-Host "  ==========================================" -ForegroundColor Cyan
Write-Host "   ByteFlow Companion - Full Desktop Mode" -ForegroundColor Cyan
Write-Host "  ==========================================" -ForegroundColor Cyan
Write-Host ""

# Find best model
$models = ollama list 2>$null | Select-String -Pattern "^\S+" | ForEach-Object {
    ($_.Matches.Value -replace ":latest","")
} | Where-Object { $_ -ne "NAME" -and $_ -ne "" }

$preferred = @("llama3","my-buddy","mistral","phi")
$model = $null
foreach ($p in $preferred) { if ($models -contains $p) { $model = $p; break } }
if (-not $model) { $model = $models[0] }

Write-Host "  Model: $model" -ForegroundColor Green
Write-Host "  Starting Ollama..." -ForegroundColor Gray
Start-Process "ollama" -ArgumentList "serve" -WindowStyle Minimized -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

Write-Host "  Launching ByteFlow Companion..." -ForegroundColor Gray
Write-Host "  (A robot character will appear on your screen)" -ForegroundColor Yellow
Write-Host "  Right-click the robot to quit." -ForegroundColor Gray
Write-Host ""

python -m byteflow.companion_core --model $model
