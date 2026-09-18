# ByteFlow Companion Launcher
$Host.UI.RawUI.WindowTitle = "ByteFlow Companion"
Set-Location $PSScriptRoot
$env:PYTHONPATH = $PSScriptRoot

Write-Host ""
Write-Host "  ==========================================" -ForegroundColor Cyan
Write-Host "   ByteFlow Companion v3" -ForegroundColor Cyan
Write-Host "  ==========================================" -ForegroundColor Cyan
Write-Host ""

# Find best model
$models = (ollama list 2>$null) -split "`n" |
    Where-Object { $_ -notmatch "NAME|^$" } |
    ForEach-Object { ($_ -split "\s+")[0] -replace ":latest","" } |
    Where-Object { $_ }

$preferred = @("qwen2.5-coder","llama3","my-buddy","mistral","phi")
$model = $null
foreach ($p in $preferred) {
    if ($models | Where-Object { $_ -like "$p*" }) { $model = $p; break }
}
if (-not $model -and $models) { $model = $models[0] }
if (-not $model) { $model = "llama3" }

Write-Host "  Model : $model" -ForegroundColor Green
Write-Host ""
Write-Host "  Aliases you can say or type:" -ForegroundColor Gray
Write-Host "    q1  = qwen2.5-coder:1.5b" -ForegroundColor Yellow
Write-Host "    l3  = llama3" -ForegroundColor Yellow
Write-Host "    mb  = my-buddy" -ForegroundColor Yellow
Write-Host "    m   = mistral" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Starting Ollama..." -ForegroundColor Gray
Start-Process "ollama" -ArgumentList "serve" -WindowStyle Minimized -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

Write-Host "  Launching companion orb..." -ForegroundColor Cyan
Write-Host "  Right-click the orb to quit." -ForegroundColor Gray
Write-Host ""

python byteflow/companion.py --model $model
