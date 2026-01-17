# Git Initialization Script
# Run this to push your project to GitHub

Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "GIT REPOSITORY SETUP" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""

# Check if git is installed
Write-Host "Checking git installation..." -ForegroundColor Yellow
try {
    $gitVersion = git --version
    Write-Host "✅ $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Git not found" -ForegroundColor Red
    Write-Host "Install from: https://git-scm.com/download/win" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Initialize git repository
Write-Host "Initializing git repository..." -ForegroundColor Yellow
if (Test-Path ".git") {
    Write-Host "⚠️  Repository already initialized" -ForegroundColor Yellow
} else {
    git init
    Write-Host "✅ Repository initialized" -ForegroundColor Green
}

Write-Host ""

# Create .gitignore if not exists
if (!(Test-Path ".gitignore")) {
    Write-Host "Creating .gitignore..." -ForegroundColor Yellow
    # Already exists, just verify
    Write-Host "✅ .gitignore exists" -ForegroundColor Green
}

Write-Host ""

# Stage all files
Write-Host "Staging files..." -ForegroundColor Yellow
git add .
Write-Host "✅ Files staged" -ForegroundColor Green

Write-Host ""

# Create initial commit
Write-Host "Creating initial commit..." -ForegroundColor Yellow
git commit -m "Initial commit: Production-grade local AI agent

Features:
- Layered architecture (Input, Reasoning, Planning, Execution, Observation, Safety)
- Local LLM integration (Ollama)
- Desktop automation (pyautogui)
- Browser automation (Playwright)
- Safety controls (kill switch, whitelists, action limits)
- Comprehensive documentation (5 guides)
- Production-grade code (type hints, logging, error handling)

Built for research, interviews, and real-world automation."

Write-Host "✅ Initial commit created" -ForegroundColor Green

Write-Host ""

# Set main branch
Write-Host "Setting main branch..." -ForegroundColor Yellow
git branch -M main
Write-Host "✅ Branch set to main" -ForegroundColor Green

Write-Host ""

# Add remote
Write-Host "Adding remote repository..." -ForegroundColor Yellow
$remoteUrl = "https://github.com/divyanshu-iitian/Agentic.git"

try {
    git remote add origin $remoteUrl
    Write-Host "✅ Remote added: $remoteUrl" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Remote 'origin' already exists" -ForegroundColor Yellow
    git remote set-url origin $remoteUrl
    Write-Host "✅ Remote URL updated" -ForegroundColor Green
}

Write-Host ""

# Show status
Write-Host "Repository status:" -ForegroundColor Yellow
git status

Write-Host ""
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "READY TO PUSH!" -ForegroundColor Green
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Make sure the GitHub repository exists:" -ForegroundColor White
Write-Host "     https://github.com/divyanshu-iitian/Agentic" -ForegroundColor White
Write-Host ""
Write-Host "  2. Push to GitHub:" -ForegroundColor White
Write-Host "     git push -u origin main" -ForegroundColor Cyan
Write-Host ""
Write-Host "  3. Add a description on GitHub:" -ForegroundColor White
Write-Host "     'Production-grade local AI agent for desktop & browser automation'" -ForegroundColor Gray
Write-Host ""
Write-Host "  4. Add topics:" -ForegroundColor White
Write-Host "     ai-agents, automation, local-llm, ollama, python, research" -ForegroundColor Gray
Write-Host ""
