<#
.SYNOPSIS
    One-click setup and run script for the RevGuard Hackathon Project.
.DESCRIPTION
    This script sets up the Python virtual environment, installs backend dependencies,
    installs frontend dependencies, runs database migrations, and boots both the 
    FastAPI backend and Next.js frontend concurrently.
#>

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "🚀 Starting RevGuard Local Setup Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$RootPath = $PSScriptRoot
$BackendPath = $RootPath
$FrontendPath = Join-Path $RootPath "template-overview-main"

# 1. Setup Python Virtual Environment
Write-Host "`n[1/5] Checking Python Virtual Environment..." -ForegroundColor Yellow
if (-not (Test-Path "$BackendPath\venv")) {
    Write-Host "Creating virtual environment..."
    python -m venv "$BackendPath\venv"
} else {
    Write-Host "Virtual environment already exists." -ForegroundColor Green
}

# 2. Install Backend Dependencies
Write-Host "`n[2/5] Installing Backend Dependencies..." -ForegroundColor Yellow
& "$BackendPath\venv\Scripts\python.exe" -m pip install -r "$BackendPath\requirements.txt"
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to install backend dependencies." -ForegroundColor Red
    exit 1
}

# 3. Setup Database (Alembic Migrations)
Write-Host "`n[3/5] Running Database Migrations..." -ForegroundColor Yellow
& "$BackendPath\venv\Scripts\python.exe" -m alembic upgrade head
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to run database migrations." -ForegroundColor Red
    exit 1
}

# 4. Install Frontend Dependencies
Write-Host "`n[4/5] Checking Frontend Dependencies..." -ForegroundColor Yellow
if (-not (Test-Path "$FrontendPath\node_modules")) {
    Write-Host "Installing Next.js dependencies (this might take a minute)..."
    Push-Location $FrontendPath
    npm install
    Pop-Location
} else {
    Write-Host "Frontend dependencies already installed." -ForegroundColor Green
}

# 5. Boot Both Servers Concurrently
Write-Host "`n[5/5] Booting up the application..." -ForegroundColor Yellow
Write-Host "Backend will run on http://localhost:8000" -ForegroundColor Green
Write-Host "Frontend will run on http://localhost:3000" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop both servers.`n" -ForegroundColor DarkGray

# Start backend in a separate background job
$BackendJob = Start-Job -ScriptBlock {
    param($Path)
    Set-Location $Path
    & "$Path\venv\Scripts\python.exe" -m uvicorn app.main:app --reload --port 8000
} -ArgumentList $BackendPath

# Start frontend in the current console
Push-Location $FrontendPath
npm run dev
Pop-Location

# If frontend stops (e.g. user hits Ctrl+C), cleanup the backend job
Write-Host "`nShutting down backend server..." -ForegroundColor Yellow
Stop-Job -Job $BackendJob
Remove-Job -Job $BackendJob
Write-Host "✅ RevGuard stopped successfully." -ForegroundColor Green
