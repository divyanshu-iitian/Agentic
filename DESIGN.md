# Design Document

## System Architecture

### Overview
Agentic is a layered autonomous agent system that follows the observe-reason-plan-execute-feedback loop.

### Core Design Principles

1. **Modularity**: Each layer is independent and testable
2. **Safety-First**: Multiple layers of validation and emergency controls
3. **Determinism**: Prefer predictable behavior over clever heuristics
4. **Observability**: Extensive logging and state tracking
5. **Offline-Capable**: No dependency on external APIs

---

## Layer Breakdown

### 1. Input Layer (UI)
**Purpose**: Accept user commands and provide feedback

**Components**:
- `ui/floating_input.py`: Tkinter-based always-on-top window
- Hotkey activation (Ctrl+Space)
- Non-blocking command queue

**Design Decisions**:
- Tkinter over PyQt: No external dependencies, sufficient for simple UI
- Always-on-top: Agent needs to be accessible without window switching
- Thread-based: UI runs in separate thread to avoid blocking agent loop

---

### 2. Reasoning Layer (LLM)
**Purpose**: Convert observations to structured actions

**Components**:
- `llm/ollama_client.py`: Local LLM communication
- `llm/prompt.py`: System prompt (most critical component)
- `llm/parser.py`: Robust JSON extraction

**Design Decisions**:
- JSON-only output: Prevents hallucination and chat-like responses
- Strict prompt: Explicitly lists allowed actions
- Low temperature (0.1): Deterministic behavior
- Few-shot examples: Improves adherence to format

**Why Ollama?**
- Simple API vs llama.cpp
- Built-in model management
- Good context window handling
- Community support

---

### 3. Planning Layer
**Purpose**: Validate and filter actions before execution

**Components**:
- `planning/action_validator.py`: Safety checks
- `planning/task_planner.py`: (Future) Multi-step decomposition

**Design Decisions**:
- Whitelist-based: Explicit allow-list for apps and domains
- Pre-execution validation: Never execute invalid actions
- Modular rules: Easy to add new validation logic

---

### 4. Execution Layer
**Purpose**: Perform desktop and browser actions

**Components**:
- `execution/desktop_executor.py`: pyautogui, keyboard
- `execution/browser_executor.py`: Playwright
- `execution/actions.py`: Pydantic schemas

**Design Decisions**:
- Pydantic validation: Type-safe action parsing
- Async browser control: Non-blocking operations
- Error handling: Actions return success/failure explicitly
- Separate executors: Clear separation of concerns

**Why Playwright over Selenium?**
- Modern async API
- Better headless support
- Cleaner DOM access
- Built-in waiting mechanisms

---

### 5. Observation Layer
**Purpose**: Capture and summarize environment state

**Components**:
- `observation/screen_capture.py`: Screenshots and OCR
- `observation/dom_parser.py`: (Future) Advanced DOM summarization
- `observation/state_detector.py`: (Future) Change detection

**Design Decisions**:
- OCR optional: Heavy operation, disabled by default
- DOM summarization: Extract only essential elements
- Lightweight defaults: Prefer speed over completeness

**Why EasyOCR?**
- Offline-capable
- Multiple languages
- Acceptable accuracy
- (Alternative: Tesseract if needed)

---

### 6. Safety Layer
**Purpose**: Emergency controls and limit enforcement

**Components**:
- `safety/kill_switch.py`: Emergency stop (Ctrl+Alt+Q)
- `safety/limiter.py`: Action count limits
- `safety/whitelist.py`: (Future) Advanced filtering

**Design Decisions**:
- Multiple kill mechanisms: Hotkey + callback
- Proactive limits: Stop before damage
- Logged warnings: Alert on limit approach

---

## Data Flow

```
User Input
    ↓
UI Thread → Main Thread → Agent
    ↓
OBSERVE: Screen + DOM → Observation String
    ↓
REASON: LLM(Observation, Task) → JSON Action
    ↓
VALIDATE: Safety Checks → Pass/Fail
    ↓
EXECUTE: Desktop/Browser Executor → Result
    ↓
FEEDBACK: Update State → Next Iteration
```

---

## Key Design Decisions

### 1. Why JSON-Only Output?
**Problem**: LLMs tend to explain, chat, and deviate from format.

**Solution**: Strict system prompt + JSON validation

**Benefits**:
- Eliminates parsing ambiguity
- Forces structured thinking
- No "I will now..." or explanations
- Easier error handling

### 2. Why Local LLM?
**Problem**: API costs, privacy, latency, internet dependency

**Solution**: Ollama + GGUF models

**Trade-offs**:
- Slower inference (acceptable for automation)
- Limited context vs GPT-4 (sufficient for step-by-step)
- Hardware requirements (mitigated by small models)

### 3. Why Observation-Based Execution?
**Problem**: Blind execution leads to errors

**Solution**: Always observe before deciding

**Benefits**:
- Self-correction capability
- Adaptive to environment changes
- Better debugging (logged observations)

### 4. Why Separate Desktop and Browser Executors?
**Problem**: Mixed concerns, hard to maintain

**Solution**: Clear separation by domain

**Benefits**:
- Easier testing
- Independent evolution
- Clearer error attribution

---

## Error Handling Strategy

### Levels of Recovery

1. **Action-level**: Executor returns error, agent continues
2. **Validation-level**: Reject action, stop task
3. **Safety-level**: Kill switch, immediate termination

### Logging Philosophy

- **DEBUG**: Internal state, LLM responses
- **INFO**: Actions, observations, results
- **WARNING**: Limits approached, retries
- **ERROR**: Failures, validation errors
- **CRITICAL**: Emergency stops, system failures

---

## Testing Strategy

### Unit Tests (Future)
- Action parsing
- JSON extraction
- Validation logic
- Executor mocking

### Integration Tests (Future)
- End-to-end task execution
- Browser automation flows
- Error recovery scenarios

### Manual Testing
- Simple tasks (calculator, notepad)
- Browser searches
- Multi-step workflows
- Emergency controls

---

## Performance Considerations

### Bottlenecks
1. **LLM Inference**: 1-5s per action
2. **OCR**: 2-3s if enabled
3. **Browser Loading**: 1-2s per page

### Optimizations
- Disable OCR by default
- Use smaller LLM models (3B params)
- Cache browser instance
- Minimize observation payload

---

## Security Considerations

### Threat Model
- **User error**: Dangerous commands
- **LLM mistakes**: Unintended actions
- **Infinite loops**: Resource exhaustion

### Mitigations
- Whitelists for apps and domains
- Action count limits
- Emergency kill switch
- No file deletion / system changes
- Logged audit trail

---

## Future Improvements

### Phase 2
- [ ] Multi-step task planning
- [ ] Better error recovery
- [ ] Persistent memory (SQLite)
- [ ] Advanced DOM parsing

### Phase 3
- [ ] Multimodal LLM (LLaVA for vision)
- [ ] Voice input (Whisper)
- [ ] Tool use (calculator, file parser)
- [ ] Learning from corrections

### Phase 4 (Research)
- [ ] RLHF loop
- [ ] Self-reflection
- [ ] Benchmark on WebArena / OSWorld
- [ ] Research paper

---

## Known Limitations

1. **No long-term memory**: Resets per session
2. **Single-threaded**: One task at a time
3. **Limited vision**: OCR only, no image understanding
4. **Windows-focused**: Needs testing on Linux/Mac
5. **No natural language feedback**: Agent doesn't explain actions

---

## Lessons Learned

1. **System prompt is everything**: More important than model size
2. **JSON parsing is hard**: Even with strict prompts
3. **Observation bandwidth**: Too much context slows LLM
4. **Safety cannot be an afterthought**: Build it in from start

---

## Comparison to Alternatives

| Feature | Agentic | AutoGPT | OpenInterpreter |
|---------|---------|---------|-----------------|
| **Offline** | ✅ | ❌ | ❌ |
| **Desktop Control** | ✅ | ❌ | Limited |
| **Browser Control** | ✅ | ✅ | Limited |
| **GUI** | ✅ | ❌ | ❌ |
| **Safety Controls** | ✅✅ | ⚠️ | ⚠️ |
| **Cost** | Free | Paid API | Paid API |

---

## References

- [Ollama Documentation](https://ollama.ai/docs)
- [Playwright Documentation](https://playwright.dev/)
- [ReAct Pattern](https://arxiv.org/abs/2210.03629)
- [WebArena Benchmark](https://webarena.dev/)

---

**Author**: Divyanshu  
**Last Updated**: January 2026
