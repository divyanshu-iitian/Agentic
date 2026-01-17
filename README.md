# Agentic — Local AI Desktop & Browser Automation Agent

**A research-grade, fully offline autonomous AI agent for desktop and browser control**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

---

## 🎯 Project Vision

Agentic is a production-grade autonomous AI agent that:
- Runs **100% offline** using local open-source LLMs
- Controls desktop applications and web browsers via natural language
- Operates through a persistent, always-on-top interface
- Plans multi-step tasks and self-corrects through observation
- Maintains strict safety boundaries and emergency controls

**Built for**: Research engineers, technical interviews, and real-world automation

---

## 🏗️ System Architecture

### Layered Agent Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    INPUT LAYER                          │
│  • Persistent floating UI (Tkinter)                     │
│  • Hotkey activation (Ctrl+Space)                       │
│  • Non-blocking command queue                           │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                   REASONING LAYER                       │
│  • Local LLM (Ollama: Qwen/LLaMA/Mistral)              │
│  • Strict system prompt                                 │
│  • JSON-only output enforcement                         │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                   PLANNING LAYER                        │
│  • Intent → Action translation                          │
│  • Multi-step task decomposition                        │
│  • Retry logic & failure handling                       │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                  EXECUTION LAYER                        │
│  • Desktop Executor (pyautogui, keyboard)              │
│  • Browser Executor (Playwright)                        │
│  • Action validation & logging                          │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                 OBSERVATION LAYER                       │
│  • Screenshot capture (Pillow)                          │
│  • OCR processing (EasyOCR)                            │
│  • DOM summarization (Playwright)                       │
│  • State change detection                               │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                    SAFETY LAYER                         │
│  • Emergency kill switch (Ctrl+Alt+Q)                  │
│  • Action limit enforcement                             │
│  • App/domain whitelist                                 │
│  • Destructive action prevention                        │
└─────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
Agentic/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── config.yaml                  # Agent configuration
├── .gitignore
│
├── main.py                      # Entry point
│
├── core/
│   ├── __init__.py
│   ├── agent.py                 # Main agent orchestration loop
│   ├── config.py                # Configuration management
│   └── state.py                 # Task state tracking
│
├── llm/
│   ├── __init__.py
│   ├── ollama_client.py         # Ollama integration
│   ├── prompt.py                # System prompt template
│   └── parser.py                # JSON output parser
│
├── planning/
│   ├── __init__.py
│   ├── task_planner.py          # Task decomposition
│   └── action_validator.py     # Action safety checks
│
├── execution/
│   ├── __init__.py
│   ├── desktop_executor.py     # Desktop automation
│   ├── browser_executor.py     # Browser automation
│   └── actions.py               # Action schemas
│
├── observation/
│   ├── __init__.py
│   ├── screen_capture.py       # Screenshot & OCR
│   ├── dom_parser.py            # Browser DOM extraction
│   └── state_detector.py       # Change detection
│
├── safety/
│   ├── __init__.py
│   ├── kill_switch.py           # Emergency controls
│   ├── whitelist.py             # App/domain filters
│   └── limiter.py               # Rate limiting
│
├── ui/
│   ├── __init__.py
│   └── floating_input.py       # Tkinter UI
│
└── utils/
    ├── __init__.py
    ├── logger.py                # Logging setup
    └── helpers.py               # Utility functions
```

---

## 🛠️ Tech Stack (100% Free & Open-Source)

| Component | Technology | Reason |
|-----------|-----------|---------|
| **LLM** | Ollama (Qwen-2.5, LLaMA-3, Mistral) | Local inference, GGUF support |
| **Language** | Python 3.10+ | Async support, rich ecosystem |
| **UI** | Tkinter | Built-in, lightweight, always-on-top |
| **Desktop Control** | pyautogui, keyboard, mouse | Cross-platform automation |
| **Browser Control** | Playwright | Modern, async, headless support |
| **OCR** | EasyOCR | GPU-accelerated, offline |
| **Image Processing** | Pillow | Standard library |
| **Memory** | JSON files | Simple, debuggable, no DB overhead |

---

## 🚀 Installation

### Prerequisites

1. **Python 3.10+**
   ```bash
   python --version
   ```

2. **Ollama** (for local LLM)
   ```bash
   # Install from https://ollama.ai
   ollama pull qwen2.5:7b
   # or
   ollama pull llama3.2:3b
   ```

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/divyanshu-iitian/Agentic.git
   cd Agentic
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   # Windows
   .\venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

4. **Configure the agent**
   ```bash
   # Edit config.yaml with your preferences
   notepad config.yaml
   ```

5. **Run the agent**
   ```bash
   python main.py
   ```

---

## 📖 Usage

### Basic Command Flow

1. Press **Ctrl+Space** to activate the input box
2. Type your natural language command:
   - "search best laptop under 80k and summarize"
   - "open notepad and type hello world"
   - "go to github and extract trending repos"
3. Press **Enter** — the agent executes autonomously
4. Press **Ctrl+Alt+Q** for emergency stop

### Example Tasks

```
User: "search Python async tutorial and save top 3 links"
Agent: browser_open → browser_search → browser_scroll → browser_extract → stop

User: "open calculator and calculate 15% of 50000"
Agent: open_app → click → type → click → stop
```

---

## 🔒 Safety Features

| Feature | Implementation | Purpose |
|---------|---------------|---------|
| **Kill Switch** | Ctrl+Alt+Q hotkey | Instant termination |
| **Action Limit** | 50 actions per task | Prevent infinite loops |
| **Whitelist** | config.yaml | Control allowed apps/domains |
| **No Destructive Ops** | Hardcoded blocks | No file deletion, no system changes |
| **Observation-Based** | Before every action | Prevents blind execution |

---

## 🧠 How It Works

### The Agent Loop (Simplified)

```python
while not task_complete:
    # 1. OBSERVE
    observation = capture_screen() + extract_dom()
    
    # 2. REASON
    action_json = llm.decide(system_prompt, observation, task)
    
    # 3. VALIDATE
    if not safety_check(action_json):
        stop()
    
    # 4. EXECUTE
    result = executor.run(action_json)
    
    # 5. FEEDBACK
    update_state(result)
```

### Why JSON-Only Output?

- Prevents hallucination
- Enables deterministic parsing
- Forces structured reasoning
- Eliminates chat-like responses

---

## 🎓 Design Decisions

### Why Ollama over llama.cpp?

- Simpler API
- Built-in model management
- Better memory handling for long contexts

### Why Playwright over Selenium?

- Modern async/await syntax
- Better headless support
- Built-in network interception
- Cleaner DOM access

### Why Tkinter over PyQt?

- No external dependencies
- Lightweight
- Sufficient for simple UI
- Cross-platform

### Why JSON Memory over Vector DB?

- No external dependencies
- Easy to debug
- Sufficient for short-term memory
- Can upgrade later without breaking architecture

---

## 🚧 Current Limitations

1. **No long-term memory** — resets per session
2. **Limited vision** — OCR only, no multimodal LLM yet
3. **Windows-optimized** — Linux/Mac need testing
4. **Single-task** — no parallel execution
5. **No learning** — no fine-tuning or RLHF loop

---

## 🛣️ Roadmap

### Phase 1 (Current) — Core Functionality
- [x] Architecture design
- [x] System prompt engineering
- [ ] Desktop automation
- [ ] Browser automation
- [ ] Basic UI
- [ ] Safety controls

### Phase 2 — Intelligence
- [ ] Multi-step task planning
- [ ] Error recovery & retry logic
- [ ] Context window management
- [ ] Action history tracking

### Phase 3 — Advanced Features
- [ ] Multimodal LLM (LLaVA)
- [ ] Voice input (Whisper)
- [ ] Persistent memory (SQLite)
- [ ] Multi-agent coordination
- [ ] Tool use (calculator, file parser)

### Phase 4 — Research Extensions
- [ ] Reinforcement learning from human feedback
- [ ] Self-improvement through reflection
- [ ] Benchmark on standard agent tasks
- [ ] Research paper submission

---

## 🤝 Contributing

This is a research project. Contributions welcome!

**Focus areas:**
- Cross-platform compatibility
- Action robustness
- Safety improvements
- Better observation methods

---

## 📜 License

MIT License — see LICENSE file

---

## 🙏 Acknowledgments

- Ollama team for local LLM infrastructure
- Playwright team for modern browser automation
- Open-source LLM community (Meta, Mistral, Qwen)

---

## 📧 Contact

**Author**: Divyanshu  
**GitHub**: [@divyanshu-iitian](https://github.com/divyanshu-iitian)  
**Project**: [Agentic](https://github.com/divyanshu-iitian/Agentic)

---

**Built with 🧠 for research, interviews, and real-world automation**
