# 📊 VISUAL ARCHITECTURE DIAGRAMS

## System Architecture (High-Level)

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                        AGENTIC AI AGENT                          ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

┌─────────────────────────────────────────────────────────────────┐
│                         INPUT LAYER                             │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Floating UI (Tkinter) — Always-on-top                    │  │
│  │  • Hotkey: Ctrl+Space                                     │  │
│  │  • Natural Language Input                                 │  │
│  │  • Status Display                                         │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                       REASONING LAYER                           │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  LLM (Ollama) — Qwen/LLaMA/Mistral                       │  │
│  │  • System Prompt (JSON-only)                              │  │
│  │  • Observation Context                                    │  │
│  │  • One Action at a Time                                   │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                       PLANNING LAYER                            │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Action Validator                                         │  │
│  │  • Whitelist Check (Apps/Domains)                        │  │
│  │  • Blocked Action Filter                                 │  │
│  │  • Safety Constraints                                    │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      EXECUTION LAYER                            │
│  ┌─────────────────────────┐  ┌──────────────────────────────┐  │
│  │  Desktop Executor       │  │  Browser Executor            │  │
│  │  • PyAutoGUI            │  │  • Playwright                │  │
│  │  • Keyboard/Mouse       │  │  • DOM Parsing               │  │
│  │  • App Launching        │  │  • Navigation                │  │
│  └─────────────────────────┘  └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     OBSERVATION LAYER                           │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  State Capture                                            │  │
│  │  • Screenshots (Pillow)                                   │  │
│  │  • OCR (EasyOCR - optional)                              │  │
│  │  • DOM Summarization                                     │  │
│  │  • Action Results                                        │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        SAFETY LAYER                             │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Emergency Controls                                       │  │
│  │  • Kill Switch (Ctrl+Alt+Q)                              │  │
│  │  • Action Limiter (50 max)                               │  │
│  │  • Whitelist Enforcement                                 │  │
│  │  • State Persistence                                     │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Agent Loop (Detailed)

```
                    ╔═══════════════════╗
                    ║   TASK STARTED    ║
                    ╚═══════════════════╝
                            │
                            ↓
                  ┌─────────────────────┐
                  │  Initialize State   │
                  │  • Reset counters   │
                  │  • Clear history    │
                  └─────────────────────┘
                            │
                            ↓
        ╔═══════════════════════════════════════════════╗
        ║                                               ║
        ║              MAIN AGENT LOOP                  ║
        ║                                               ║
        ╠═══════════════════════════════════════════════╣
        ║                                               ║
        ║  ┌─────────────────────────────────────────┐ ║
        ║  │ STEP 1: OBSERVE                         │ ║
        ║  │ • Capture screen state                  │ ║
        ║  │ • Extract DOM (if browser active)       │ ║
        ║  │ • Get previous action result            │ ║
        ║  └─────────────────────────────────────────┘ ║
        ║                  │                            ║
        ║                  ↓                            ║
        ║  ┌─────────────────────────────────────────┐ ║
        ║  │ STEP 2: REASON                          │ ║
        ║  │ • Build prompt (system + observation)   │ ║
        ║  │ • Query LLM (Ollama)                    │ ║
        ║  │ • Parse JSON response                   │ ║
        ║  └─────────────────────────────────────────┘ ║
        ║                  │                            ║
        ║                  ↓                            ║
        ║  ┌─────────────────────────────────────────┐ ║
        ║  │ STEP 3: VALIDATE                        │ ║
        ║  │ • Check whitelist                       │ ║
        ║  │ • Verify action limit                   │ ║
        ║  │ • Block dangerous actions               │ ║
        ║  └─────────────────────────────────────────┘ ║
        ║                  │                            ║
        ║                  ├───→ Invalid → STOP        ║
        ║                  │                            ║
        ║                  ↓ Valid                      ║
        ║  ┌─────────────────────────────────────────┐ ║
        ║  │ STEP 4: EXECUTE                         │ ║
        ║  │ • Desktop OR Browser executor           │ ║
        ║  │ • Perform action                        │ ║
        ║  │ • Capture result                        │ ║
        ║  └─────────────────────────────────────────┘ ║
        ║                  │                            ║
        ║                  ↓                            ║
        ║  ┌─────────────────────────────────────────┐ ║
        ║  │ STEP 5: FEEDBACK                        │ ║
        ║  │ • Update state                          │ ║
        ║  │ • Log action                            │ ║
        ║  │ • Save history                          │ ║
        ║  └─────────────────────────────────────────┘ ║
        ║                  │                            ║
        ║                  ↓                            ║
        ║         [Action = "stop"?]                    ║
        ║                  │                            ║
        ║        No ←──────┴──────→ Yes                 ║
        ║        │                  │                   ║
        ╚════════╪══════════════════╪═══════════════════╝
                 │                  │
      (loop back)                   ↓
                           ┌─────────────────┐
                           │  TASK COMPLETE  │
                           └─────────────────┘
```

---

## Data Flow

```
┌────────────┐
│    USER    │ Types: "search best laptop under 80k"
└────────────┘
      │
      ↓
┌─────────────────────────────────────────────────┐
│  INPUT LAYER (ui/floating_input.py)             │
│  • Receives command                             │
│  • Queues for processing                        │
└─────────────────────────────────────────────────┘
      │
      ↓
┌─────────────────────────────────────────────────┐
│  AGENT ORCHESTRATOR (core/agent.py)             │
│  • Starts task                                  │
│  • Initializes state                            │
└─────────────────────────────────────────────────┘
      │
      ↓
┌─────────────────────────────────────────────────┐
│  OBSERVATION (observation/screen_capture.py)    │
│  → Screen: 1920x1080                            │
│  → Browser: Not active                          │
└─────────────────────────────────────────────────┘
      │
      ↓
┌─────────────────────────────────────────────────┐
│  LLM REASONING (llm/ollama_client.py)           │
│  Prompt: "Task: search best laptop under 80k    │
│           Observation: Screen 1920x1080         │
│           Your next action (JSON only):"        │
│                                                 │
│  Response: {"action":"browser_open",            │
│             "args":{"url":"https://google.com"}}│
└─────────────────────────────────────────────────┘
      │
      ↓
┌─────────────────────────────────────────────────┐
│  JSON PARSER (llm/parser.py)                    │
│  • Extracts JSON from response                  │
│  • Validates structure                          │
│  → action: "browser_open"                       │
│  → args: {"url": "https://google.com"}          │
└─────────────────────────────────────────────────┘
      │
      ↓
┌─────────────────────────────────────────────────┐
│  VALIDATOR (planning/action_validator.py)       │
│  • Check: google.com in allowed_domains? ✅     │
│  • Check: browser_open blocked? ❌              │
│  → Action APPROVED                              │
└─────────────────────────────────────────────────┘
      │
      ↓
┌─────────────────────────────────────────────────┐
│  BROWSER EXECUTOR (execution/browser_executor.py│
│  • Launch Chromium                              │
│  • Navigate to https://google.com               │
│  • Wait for page load                           │
│  → Success: True                                │
└─────────────────────────────────────────────────┘
      │
      ↓
┌─────────────────────────────────────────────────┐
│  STATE UPDATE (core/state.py)                   │
│  • Increment step_count                         │
│  • Add to action_history                        │
│  • Update last_result                           │
│  • Save to state/current_task.json              │
└─────────────────────────────────────────────────┘
      │
      ↓ (loop continues...)
```

---

## Module Dependencies

```
                    main.py
                       │
          ┌────────────┼────────────┐
          ↓            ↓            ↓
    core/agent   ui/floating   utils/logger
          │            │
          ↓            ↓
    ┌─────────────────────────┐
    │     Core Modules         │
    ├─────────────────────────┤
    │  • core/state.py        │
    │  • core/config.py       │
    └─────────────────────────┘
          │
          ↓
    ┌─────────────────────────────────────────┐
    │           LLM Layer                     │
    ├─────────────────────────────────────────┤
    │  • llm/ollama_client.py                 │
    │  • llm/prompt.py                        │
    │  • llm/parser.py                        │
    └─────────────────────────────────────────┘
          │
          ├──→ planning/action_validator.py
          │
          ├──→ execution/
          │    ├── actions.py
          │    ├── desktop_executor.py
          │    └── browser_executor.py
          │
          ├──→ observation/screen_capture.py
          │
          └──→ safety/kill_switch.py
```

---

## Action Schema (Pydantic)

```
                  AgentAction
                       │
        ┌──────────────┼──────────────┐
        ↓              ↓              ↓
  DesktopActions  BrowserActions  ControlActions
        │              │              │
        ├─ open_app    ├─ browser_open     └─ stop
        ├─ click       ├─ browser_search
        ├─ type        ├─ browser_click
        ├─ scroll      ├─ browser_scroll
        └─ wait        └─ browser_extract

Each action is a Pydantic model with:
  • action: Literal["action_name"]
  • args: Dict[str, Any]
  • validate_args() method
```

---

## Safety Layers

```
                    User Command
                         │
                         ↓
            ┌────────────────────────┐
            │  Layer 1: Whitelist    │
            │  Check app/domain      │
            └────────────────────────┘
                         │
                     Valid? ──No──→ REJECT
                         │
                        Yes
                         ↓
            ┌────────────────────────┐
            │  Layer 2: Blocked List │
            │  Check action type     │
            └────────────────────────┘
                         │
                  Blocked? ──Yes──→ REJECT
                         │
                        No
                         ↓
            ┌────────────────────────┐
            │  Layer 3: Action Limit │
            │  Count < 50?           │
            └────────────────────────┘
                         │
                   Exceeded? ──Yes──→ STOP
                         │
                        No
                         ↓
            ┌────────────────────────┐
            │  Layer 4: Kill Switch  │
            │  Ctrl+Alt+Q pressed?   │
            └────────────────────────┘
                         │
                  Triggered? ──Yes──→ ABORT
                         │
                        No
                         ↓
                 EXECUTE ACTION
```

---

## File Organization Philosophy

```
Agentic/
│
├── Top-level: Entry points & config
│   • main.py (start here)
│   • config.yaml (configure here)
│   • requirements.txt (install these)
│
├── Modules: Functional grouping
│   • core/ → Orchestration
│   • llm/ → Intelligence
│   • execution/ → Actions
│   • observation/ → Perception
│   • safety/ → Protection
│   • ui/ → Interface
│   • utils/ → Helpers
│
└── Documentation: User guides
    • README.md → Overview
    • QUICKSTART.md → Get started
    • ARCHITECTURE.md → Deep dive
    • EXAMPLES.md → Usage
    • ROADMAP.md → Future
```

---

## Development Workflow

```
1. User runs: python main.py
             │
             ↓
2. System initializes:
   ┌─ Load config.yaml
   ├─ Setup logger
   ├─ Initialize agent
   ├─ Start UI thread
   └─ Activate kill switch
             │
             ↓
3. User presses: Ctrl+Space
             │
             ↓
4. UI window appears
             │
             ↓
5. User types command + Enter
             │
             ↓
6. Agent loop executes
   (See "Agent Loop" diagram above)
             │
             ↓
7. Task completes
             │
             ↓
8. UI shows status: ✅ Completed
             │
             ↓
9. Ready for next command
```

---

## Error Handling Flow

```
              Try Execute Action
                     │
                     ↓
         ┌───────────────────────┐
         │   Success?            │
         └───────────────────────┘
            │              │
           Yes            No
            │              │
            ↓              ↓
    Log success    ┌───────────────────┐
    Continue       │  Catch Exception  │
                   └───────────────────┘
                           │
                           ↓
                   ┌───────────────────┐
                   │  Log error        │
                   │  Return failure   │
                   └───────────────────┘
                           │
                           ↓
                   ┌───────────────────┐
                   │  Agent decides    │
                   │  • Retry?         │
                   │  • Skip?          │
                   │  • Stop?          │
                   └───────────────────┘
```

---

**These diagrams visualize the complete system architecture.**
