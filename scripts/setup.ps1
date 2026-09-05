# ==============================================================================
# ORION BAS AI Copilot — Environment Setup (PowerShell)
# ==============================================================================
$ErrorActionPreference = "Stop"

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "🚀 ORION BAS AI Copilot — Environment Setup (Windows/PowerShell)" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "❌ 'uv' is not installed. Please install uv from https://astral.sh/uv" -ForegroundColor Red
    exit 1
}

Write-Host "✅ uv found: $(uv --version)" -ForegroundColor Green

Write-Host "📦 Setting up Python 3.11 virtual environment..." -ForegroundColor Yellow
uv venv --python 3.11 .venv
& .\.venv\Scripts\Activate.ps1

Write-Host "📦 Installing Python dependencies..." -ForegroundColor Yellow
uv pip install -e ".[all]"

if (Get-Command npm -ErrorAction SilentlyContinue) {
    Write-Host "📦 Installing frontend dependencies..." -ForegroundColor Yellow
    npm install --prefix frontend
}

Write-Host "🩺 Running system doctor diagnostic..." -ForegroundColor Yellow
python scripts\doctor.py

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "🎉 Setup complete! Activate: .\.venv\Scripts\Activate.ps1" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Cyan
