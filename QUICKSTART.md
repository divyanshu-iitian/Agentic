# Quick Start Guide

## Installation

### 1. Install Ollama (LLM Server)

Download and install from: https://ollama.ai

After installation, pull a model:

```bash
ollama pull qwen2.5:7b
# or for faster inference on lower-end hardware
ollama pull llama3.2:3b
```

Start the Ollama server:

```bash
ollama serve
```

### 2. Setup Python Environment

```bash
# Navigate to project directory
cd Agentic

# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### 3. Configure the Agent

Edit `config.yaml`:

```yaml
llm:
  model: "qwen2.5:7b"  # Change to your installed model
```

### 4. Run the Agent

```bash
python main.py
```

---

## Usage

### Activate UI
Press **Ctrl+Space** to show the input box

### Example Commands

**Desktop Automation:**
```
open calculator and compute 15% of 50000
```

**Browser Automation:**
```
search best laptop under 80k and summarize
```

**Combined:**
```
go to github trending and save the top 5 repos
```

### Emergency Stop
Press **Ctrl+Alt+Q** to immediately stop execution

---

## Troubleshooting

### Ollama Connection Error
- Make sure Ollama is running: `ollama serve`
- Check if model is installed: `ollama list`
- Verify URL in config.yaml

### Playwright Issues
```bash
playwright install chromium
```

### OCR Not Working
OCR is disabled by default for performance. Enable in config.yaml:
```yaml
observation:
  ocr_enabled: true
```

### Permission Errors
Run as administrator on Windows for some desktop actions

---

## Tips

1. **Start Simple**: Test with basic commands first
2. **Watch Logs**: Check `logs/agent.log` for details
3. **Adjust Limits**: Increase `max_actions_per_task` for complex tasks
4. **Use Whitelists**: Enable safety whitelists in production

---

## Architecture Overview

```
User Command
    ↓
[OBSERVE] → Capture screen/DOM state
    ↓
[REASON] → LLM decides next action (JSON)
    ↓
[VALIDATE] → Safety checks
    ↓
[EXECUTE] → Perform action
    ↓
[FEEDBACK] → Update state, repeat
```

---

## Next Steps

1. Test basic desktop actions
2. Test browser automation
3. Customize system prompt in `llm/prompt.py`
4. Adjust safety settings in `config.yaml`
5. Extend with new actions in `execution/actions.py`

---

## Need Help?

- Check logs in `logs/agent.log`
- Review action history in `state/action_history.json`
- See README.md for detailed documentation
