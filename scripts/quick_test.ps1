# Quick test script to verify the setup

Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host "SQL Router - Quick Setup Test" -ForegroundColor Cyan
Write-Host "==================================================`n" -ForegroundColor Cyan

$errors = 0

# Check Python
Write-Host "Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  ✓ $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Python not found" -ForegroundColor Red
    $errors++
}

# Check if virtual environment exists
Write-Host "`nChecking virtual environment..." -ForegroundColor Yellow
if (Test-Path ".venv") {
    Write-Host "  ✓ Virtual environment exists" -ForegroundColor Green
} else {
    Write-Host "  ✗ Virtual environment not found" -ForegroundColor Red
    Write-Host "    Run: python -m venv .venv" -ForegroundColor Yellow
    $errors++
}

# Check if package is installed
Write-Host "`nChecking Python package..." -ForegroundColor Yellow
try {
    $result = python -c "import sqlrouter; print(sqlrouter.__version__)" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ sqlrouter package installed (v$result)" -ForegroundColor Green
    } else {
        Write-Host "  ✗ sqlrouter package not installed" -ForegroundColor Red
        Write-Host "    Run: pip install -e ." -ForegroundColor Yellow
        $errors++
    }
} catch {
    Write-Host "  ✗ Error checking package" -ForegroundColor Red
    $errors++
}

# Check Node.js
Write-Host "`nChecking Node.js..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version 2>&1
    Write-Host "  ✓ Node.js $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Node.js not found" -ForegroundColor Red
    $errors++
}

# Check if frontend dependencies are installed
Write-Host "`nChecking frontend..." -ForegroundColor Yellow
if (Test-Path "frontend/node_modules") {
    Write-Host "  ✓ Frontend dependencies installed" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Frontend dependencies not installed" -ForegroundColor Yellow
    Write-Host "    Run: cd frontend && npm install" -ForegroundColor Yellow
}

# Check if fixtures exist
Write-Host "`nChecking fixtures..." -ForegroundColor Yellow
if (Test-Path "artifacts/results/router_config.json") {
    Write-Host "  ✓ Fixtures exist" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Fixtures not found" -ForegroundColor Yellow
    Write-Host "    Run: python scripts/make_fixtures.py" -ForegroundColor Yellow
}

# Check .env file
Write-Host "`nChecking environment configuration..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Write-Host "  ✓ .env file exists" -ForegroundColor Green
} else {
    Write-Host "  ⚠ .env file not found" -ForegroundColor Yellow
    Write-Host "    Copy .env.example to .env and configure" -ForegroundColor Yellow
}

# Summary
Write-Host "`n==================================================" -ForegroundColor Cyan
if ($errors -eq 0) {
    Write-Host "✓ Setup looks good!" -ForegroundColor Green
    Write-Host "`nQuick start:" -ForegroundColor Cyan
    Write-Host "  1. Generate fixtures:" -ForegroundColor White
    Write-Host "     python scripts/make_fixtures.py" -ForegroundColor Gray
    Write-Host "  2. Start backend:" -ForegroundColor White
    Write-Host "     MODE=replay python -m uvicorn sqlrouter.serve.main:app" -ForegroundColor Gray
    Write-Host "  3. Start frontend:" -ForegroundColor White
    Write-Host "     cd frontend && npm run dev" -ForegroundColor Gray
} else {
    Write-Host "✗ Setup incomplete ($errors errors)" -ForegroundColor Red
    Write-Host "`nPlease fix the errors above" -ForegroundColor Yellow
}
Write-Host "==================================================`n" -ForegroundColor Cyan
