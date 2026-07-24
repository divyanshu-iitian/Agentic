$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$virtualEnv = Join-Path $projectRoot ".venv"
$python = Join-Path $virtualEnv "Scripts\python.exe"
$frontend = Join-Path $projectRoot "agentic-app\frontend"

Write-Host "Setting up Agentic..." -ForegroundColor Cyan

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python 3.10 or newer is required."
}

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    throw "Node.js 20 or newer is required."
}

if (-not (Test-Path -LiteralPath $virtualEnv)) {
    python -m venv $virtualEnv
}

& $python -m pip install --upgrade pip
& $python -m pip install -r (Join-Path $projectRoot "requirements.txt")
& $python -m pip install -r (Join-Path $projectRoot "agentic-app\backend\requirements.txt")
& $python -m playwright install chromium

Push-Location $frontend
try {
    npm ci
}
finally {
    Pop-Location
}

if (Get-Command ollama -ErrorAction SilentlyContinue) {
    Write-Host "Ollama found. Pulling the default lightweight model..." -ForegroundColor Cyan
    ollama pull qwen2.5:3b
}
else {
    Write-Warning "Ollama was not found. Install it from https://ollama.com/ before starting Agentic."
}

Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host "Desktop agent: .\.venv\Scripts\python.exe main.py"
Write-Host "Chat backend:  cd agentic-app\backend; ..\..\.venv\Scripts\python.exe main.py"
Write-Host "Chat frontend: cd agentic-app\frontend; npm run dev"
