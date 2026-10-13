# PowerShell script to run backend in different modes

param(
    [ValidateSet("replay", "live")]
    [string]$Mode = "replay",
    
    [int]$Port = 8000,
    
    [switch]$Reload
)

Write-Host "Starting SQL Router backend" -ForegroundColor Green
Write-Host "Mode: $Mode" -ForegroundColor Cyan
Write-Host "Port: $Port" -ForegroundColor Cyan

# Set environment
$env:MODE = $Mode
$env:PORT = $Port

# Check if fixtures exist for replay mode
if ($Mode -eq "replay") {
    $configPath = "artifacts/results/router_config.json"
    if (-not (Test-Path $configPath)) {
        Write-Host "`nWARNING: Fixtures not found!" -ForegroundColor Yellow
        Write-Host "Run: python scripts/make_fixtures.py" -ForegroundColor Yellow
        Write-Host ""
    }
}

# Check if model exists for live mode
if ($Mode -eq "live") {
    $modelPath = "artifacts/merged/qlora_r16"
    if (-not (Test-Path $modelPath)) {
        Write-Host "`nERROR: Model not found at $modelPath" -ForegroundColor Red
        Write-Host "Run the ML pipeline (s01-s10) to generate it" -ForegroundColor Red
        exit 1
    }
}

# Build uvicorn command
$cmd = "python -m uvicorn sqlrouter.serve.main:app --host 0.0.0.0 --port $Port"

if ($Reload) {
    $cmd += " --reload"
}

Write-Host "`nStarting server..." -ForegroundColor Green
Write-Host $cmd -ForegroundColor Gray
Write-Host ""

# Run
Invoke-Expression $cmd
