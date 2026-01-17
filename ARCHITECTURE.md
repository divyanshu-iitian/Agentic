# Architecture Deep Dive

## System Design Philosophy

Agentic follows a **strict layered architecture** inspired by research-grade AI agent systems:

1. **Separation of Concerns**: Each layer has a single, well-defined responsibility
2. **Observation-Based**: Agent only acts on what it observes, not assumptions
3. **Safety-First**: Multiple safety layers prevent dangerous actions
4. **Deterministic Execution**: Minimize randomness for reproducibility
5. **Debuggability**: Every step is logged and traceable

---

## Component Breakdown

### 1. Input Layer (`ui/`)

**Purpose**: Persistent user interface

**Key Files**:
- `floating_input.py`: Tkinter-based always-on-top UI

**Design Decisions**:
- Tkinter over PyQt: No external dependencies, lighter
- Always-on-top: Quick access without disrupting workflow
- Non-blocking: UI runs in separate thread

**Future Improvements**:
- Voice input via Whisper
- System tray integration
- Command history

---

### 2. Reasoning Layer (`llm/`)

**Purpose**: LLM integration and prompt engineering

**Key Files**:
- `ollama_client.py`: Ollama server communication
- `prompt.py`: System prompt (MOST CRITICAL FILE)
- `parser.py`: Robust JSON extraction

**Design Decisions**:
- Ollama over llama.cpp: Simpler API, better UX
- JSON-only output: Prevents hallucination, enables parsing
- Low temperature (0.1): Deterministic behavior
- System prompt with examples: Few-shot learning

**Why This Matters**:
The system prompt is the **brain** of the agent. A weak prompt = unreliable agent.

**Future Improvements**:
- Dynamic few-shot examples based on task
- Chain-of-thought reasoning
- Self-reflection for error correction

---

### 3. Planning Layer (`planning/`)

**Purpose**: Task decomposition and action validation

**Key Files**:
- `action_validator.py`: Safety checks before execution

**Design Decisions**:
- Whitelist approach: Only allow known-safe apps/domains
- Fail-safe: Block > Allow for unknown actions

**Future Improvements**:
- Multi-step planning (graph-based)
- Cost estimation per action
- Alternative plan generation

---

### 4. Execution Layer (`execution/`)

**Purpose**: Perform desktop and browser actions

**Key Files**:
- `actions.py`: Pydantic schemas for type safety
- `desktop_executor.py`: pyautogui-based desktop control
- `browser_executor.py`: Playwright-based browser control

**Design Decisions**:
- Pydantic for validation: Catch errors early
- Separate executors: Clear separation of concerns
- Async browser executor: Non-blocking, modern

**Action Design**:
- Atomic: One action = one effect
- Idempotent where possible
- Clear success/failure reporting

**Future Improvements**:
- Image-based element detection (YOLO)
- Accessibility API integration (more reliable than coordinates)
- Action queuing and parallelization

---

### 5. Observation Layer (`observation/`)

**Purpose**: Perceive current state

**Key Files**:
- `screen_capture.py`: Screenshots + OCR

**Design Decisions**:
- OCR optional: Heavy, disabled by default
- DOM over screenshots for browsers: Structured data
- Lightweight observations: Fast feedback loop

**Future Improvements**:
- Multimodal LLM integration (LLaVA for screenshot understanding)
- Change detection (diff previous vs current state)
- Semantic scene understanding

---

### 6. Safety Layer (`safety/`)

**Purpose**: Emergency controls and limits

**Key Files**:
- `kill_switch.py`: Emergency stop + action limiter

**Design Decisions**:
- Hardware hotkey: Always accessible, even if UI freezes
- Action limits: Prevent infinite loops
- Whitelists: Explicit > Implicit permissions

**Future Improvements**:
- Undo mechanism for reversible actions
- Sandboxed execution environment
- User confirmation for sensitive actions

---

### 7. Core (`core/`)

**Purpose**: Orchestration and state management

**Key Files**:
- `agent.py`: Main agent loop
- `state.py`: Task state tracking
- `config.py`: Configuration management

**The Agent Loop**:
```python
while task_not_complete:
    observation = observe()      # What do I see?
    action = reason(observation) # What should I do?
    validate(action)             # Is it safe?
    result = execute(action)     # Do it
    update_state(result)         # Remember it
```

**Design Decisions**:
- Single-step execution: Simpler to debug
- Persistent state: Survives crashes
- Pydantic config: Type-safe, validated

**Future Improvements**:
- Multi-agent coordination
- Task prioritization
- Learning from failures

---

## Data Flow

```
┌─────────────┐
│  User Input │
└──────┬──────┘
       ↓
┌──────────────────────────────────────────┐
│  Agent Loop (core/agent.py)              │
│  ┌────────────────────────────────────┐  │
│  │ 1. OBSERVE                         │  │
│  │    - Screen state                  │  │
│  │    - Browser DOM                   │  │
│  └────────────────────────────────────┘  │
│           ↓                               │
│  ┌────────────────────────────────────┐  │
│  │ 2. REASON                          │  │
│  │    - Build prompt                  │  │
│  │    - Query LLM (Ollama)           │  │
│  │    - Parse JSON                    │  │
│  └────────────────────────────────────┘  │
│           ↓                               │
│  ┌────────────────────────────────────┐  │
│  │ 3. VALIDATE                        │  │
│  │    - Safety checks                 │  │
│  │    - Whitelist verification        │  │
│  └────────────────────────────────────┘  │
│           ↓                               │
│  ┌────────────────────────────────────┐  │
│  │ 4. EXECUTE                         │  │
│  │    - Desktop OR Browser executor   │  │
│  └────────────────────────────────────┘  │
│           ↓                               │
│  ┌────────────────────────────────────┐  │
│  │ 5. FEEDBACK                        │  │
│  │    - Update state                  │  │
│  │    - Log action                    │  │
│  └────────────────────────────────────┘  │
└──────────────────────────────────────────┘
```

---

## Key Architectural Patterns

### 1. **Observer Pattern**
- Agent observes environment before each action
- State changes trigger observations

### 2. **Command Pattern**
- Actions are first-class objects
- Enables logging, undo, replay

### 3. **Strategy Pattern**
- Desktop vs Browser executors
- Swappable LLM backends

### 4. **Singleton Pattern**
- Global config instance
- Logger instance

---

## Why This Architecture?

### ✅ Advantages

1. **Modularity**: Each component can be developed/tested independently
2. **Extensibility**: Add new actions without touching core loop
3. **Debuggability**: Clear data flow, extensive logging
4. **Safety**: Multiple validation layers
5. **Research-Ready**: Clean abstractions for experimentation

### ⚠️ Trade-offs

1. **Complexity**: More files/classes than monolithic script
2. **Performance**: Overhead from layers (acceptable for agent tasks)
3. **Learning Curve**: Requires understanding the architecture

---

## Comparison to Alternatives

| Aspect | Agentic | AutoGPT | LangChain Agents |
|--------|---------|---------|------------------|
| **Local LLM** | ✅ Yes | ❌ API only | ⚠️ Partial |
| **Offline** | ✅ Yes | ❌ No | ❌ No |
| **Desktop Control** | ✅ Yes | ❌ No | ❌ No |
| **Architecture** | Layered | Monolithic | Framework |
| **Research-Grade** | ✅ Yes | ⚠️ Demo | ✅ Yes |

---

## Performance Considerations

### Bottlenecks
1. **LLM Inference**: ~1-3s per action (depends on model)
2. **OCR**: ~1-2s if enabled
3. **Browser Navigation**: ~2-5s for page loads

### Optimizations
- Disable OCR by default
- Use smaller LLMs (3B parameters)
- Cache DOM summaries
- Parallel observation gathering (future)

---

## Security Considerations

### Current Protections
- Whitelist-based access control
- Action limit enforcement
- No file system access
- Emergency kill switch

### Threat Model
- **Malicious Commands**: Validated against whitelist
- **Infinite Loops**: Action limiter stops execution
- **Crashes**: State persisted to disk
- **Privacy**: All local, no data leaves machine

### Future Enhancements
- Sandboxed execution (Docker)
- User confirmation for sensitive actions
- Audit logging
- Rate limiting

---

## Testing Strategy

### Unit Tests (Future)
- Action validators
- JSON parser
- Config loader

### Integration Tests (Future)
- Full agent loop with mock LLM
- Desktop executor (headless)
- Browser executor (headless)

### End-to-End Tests (Future)
- Real task execution
- Benchmark against standard tasks

---

## Research Extensions

### Potential Research Directions

1. **Multimodal Perception**
   - Integrate vision LLMs (LLaVA)
   - Screenshot understanding without OCR

2. **Reinforcement Learning**
   - Learn from task success/failure
   - RLHF-style feedback loop

3. **Multi-Agent Systems**
   - Specialized agents (browser, desktop, data)
   - Coordination protocols

4. **Self-Improvement**
   - Reflection on failures
   - Automatic prompt refinement

5. **Benchmarking**
   - Create agent task benchmark
   - Compare to other systems

---

## Conclusion

This architecture prioritizes:
- **Correctness** over speed
- **Safety** over features
- **Clarity** over cleverness

Perfect for research, learning, and interviews.
