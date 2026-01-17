# Installation Script for Windows
# Run this in PowerShell

Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "AGENTIC AI AGENT - SETUP SCRIPT" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""

# Check Python version
Write-Host "Checking Python version..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($pythonVersion -match "Python 3\.1[0-9]") {
    Write-Host "✅ $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "❌ Python 3.10+ required. Current: $pythonVersion" -ForegroundColor Red
    Write-Host "Install from: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Create virtual environment
Write-Host "Creating virtual environment..." -ForegroundColor Yellow
if (Test-Path "venv") {
    Write-Host "⚠️  venv already exists, skipping" -ForegroundColor Yellow
} else {
    python -m venv venv
    Write-Host "✅ Virtual environment created" -ForegroundColor Green
}

Write-Host ""

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"

Write-Host ""

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet

Write-Host ""

# Install dependencies
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Python dependencies installed" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Install Playwright browsers
Write-Host "Installing Playwright browsers..." -ForegroundColor Yellow
playwright install chromium
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Playwright Chromium installed" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to install Playwright browsers" -ForegroundColor Red
}

Write-Host ""

# Create necessary directories
Write-Host "Creating project directories..." -ForegroundColor Yellow
$dirs = @("logs", "state", "screenshots")
foreach ($dir in $dirs) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
        Write-Host "  Created: $dir" -ForegroundColor Gray
    }
}
Write-Host "✅ Directories ready" -ForegroundColor Green

Write-Host ""

# Check Ollama
Write-Host "Checking Ollama installation..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 5 -UseBasicParsing 2>$null
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Ollama is running" -ForegroundColor Green
        
        # Parse models
        $data = $response.Content | ConvertFrom-Json
        $models = $data.models | ForEach-Object { $_.name }
        
        if ($models.Count -gt 0) {
            Write-Host "  Available models:" -ForegroundColor Gray
            foreach ($model in $models) {
                Write-Host "    - $model" -ForegroundColor Gray
            }
        } else {
            Write-Host "  ⚠️  No models installed" -ForegroundColor Yellow
            Write-Host "  Run: ollama pull qwen2.5:7b" -ForegroundColor Yellow
        }
    } else {
        throw "Not running"
    }
} catch {
    Write-Host "❌ Ollama is not running" -ForegroundColor Red
    Write-Host "  Install from: https://ollama.ai" -ForegroundColor Yellow
    Write-Host "  Then run: ollama serve" -ForegroundColor Yellow
    Write-Host "  And pull a model: ollama pull qwen2.5:7b" -ForegroundColor Yellow
}

Write-Host ""

# Run health check
Write-Host "Running system health check..." -ForegroundColor Yellow
python check_health.py

Write-Host ""
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "SETUP COMPLETE!" -ForegroundColor Green
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Make sure Ollama is running: ollama serve" -ForegroundColor White
Write-Host "  2. Verify you have a model: ollama pull qwen2.5:7b" -ForegroundColor White
Write-Host "  3. Run the agent: python main.py" -ForegroundColor White
Write-Host "  4. Press Ctrl+Space to activate" -ForegroundColor White
Write-Host ""
Write-Host "Documentation:" -ForegroundColor Yellow
Write-Host "  README.md        - Overview and features" -ForegroundColor White
Write-Host "  QUICKSTART.md    - Quick start guide" -ForegroundColor White
Write-Host "  ARCHITECTURE.md  - Deep dive into design" -ForegroundColor White
Write-Host ""
