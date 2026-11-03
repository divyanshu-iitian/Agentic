# Changelog

All notable changes are recorded here. Agentic follows semantic versioning.

## [0.3.0] - 2026-11-03

### Added

- computer use: 15 desktop tools. Eyes: Windows UI Automation accessibility tree,
  screenshots with a labeled coordinate grid, OCR, and a window list. Hands: click by element
  or coordinates, type (including non-ASCII on Windows), hotkeys, move, drag, draw shapes on a
  0-1000 canvas grid, scroll, wait, and focus/maximize/minimize/restore windows
- a persistent Playwright browser session with numbered-element snapshots: open, snapshot,
  click, type, select, press, scroll, back, and screenshot
- vision: images in messages for Ollama, OpenAI-compatible APIs, and Anthropic; Ollama vision
  auto-detection; screenshot tools offered only to vision models; old screenshots pruned
- MCP tool results that contain images are passed to vision models
- `navigator` head for websites and a rewritten `operator` head with an observe, act, verify loop
- `drawing` and `computer-use` skills
- emergency stop: Ctrl+Alt+Q in the CLI, or the mouse in a screen corner, halts every head,
  even mid-stroke
- chat shortcuts `/computer` and `/browse`
- `browser` permission tier for clicking and typing on websites
- `computer` config section and `doctor` checks for vision and UI Automation

### Changed

- the default context window is now 16,384 tokens so tools and screenshots fit
- the repeat guard only stops identical calls made back to back

### Fixed

- found by testing in the real Paint app: strokes made with pyautogui cursor jumps were silently
  ignored, so drawing now sends real `mouse_event` input on Windows
- bringing a window to the front pressed Alt, which opened ribbon key tips in Paint and Office
- minimized windows could not be found, so they could not be restored

## [0.2.0] - 2026-11-03

### Added

- `agentic` package and CLI (`agentic init|doctor|chat|run|swarm|serve|heads|tools|runs|schedule|memory`)
- multi-head swarms: a planner builds a task graph, specialist heads run independent tasks
  in parallel, a critic can send tasks back for revision, and a synthesizer writes the answer
- nine built-in heads defined as Markdown profiles; custom heads in `heads/` add to or
  override them, and each head can use its own provider and model
- providers: Ollama, any OpenAI-compatible API, and Anthropic, plus a prompt-based tool mode
  for small models without native tool calling
- 20 built-in tools: workspace files, regex search, shell, Python, web search, page fetch,
  headless browser, desktop control with OCR, memory, scheduling, and delegation
- MCP client over stdio; server tools are registered as `mcp__<server>__<tool>`
- approval policy per permission tier (`auto`, `ask`, `deny`) with terminal, dashboard, and
  Telegram approvers, plus a stricter policy for unattended scheduled runs
- SQLite store with FTS5 memory search, run history, a full event log, chat sessions, and
  schedules
- interval and cron schedules executed by the gateway
- gateway with the Mission Control dashboard, REST API, and a Server-Sent Events stream
- Telegram channel with long polling, allow-listed chats, and in-chat approvals
- 90 new tests covering the runtime; CI on Linux and Windows with Python 3.10 and 3.12

### Changed

- the skill registry moved to `agentic/skills.py`; `core/skills.py` re-exports it
- `pyproject.toml` now packages the project and installs the `agentic` command

### Security

- file tools refuse any path outside the workspace, including through `..` or symlinks
- web tools refuse loopback, private, link-local, and metadata addresses, including after
  redirects and for browser subresources
- a guard refuses known destructive shell commands even when they are approved
- the gateway rejects cross-origin requests and unexpected `Host` headers, and will not bind
  to a public interface unless a token is set

## [0.1.0] - 2026-07-24

### Added

- lightweight React and FastAPI application under `agentic-app/`
- local Ollama chat with an optional Groq provider
- bounded task-selected Markdown skills
- explicit-feedback long-term memory and short-lived failure reflections
- typed action schemas, URL protocol checks, allowlists, and action budgets
- Privacy Mode, reduced-motion support, and a low-redraw desktop command bar
- deterministic Python tests and cross-platform GitHub Actions

### Changed

- rebuilt the agent loop around observe, act, verify, and adapt
- made `qwen2.5:3b` the default for modest laptops
- capped prompts, histories, generations, waits, coordinates, and tool arguments
- removed inherited prototype naming and obsolete experimental components

### Security

- untrusted screen and web content is explicitly separated from user intent
- unknown actions, extra arguments, unsafe URL schemes, and shell metacharacters
  are rejected before execution
- exceptions are logged locally without exposing raw server details to clients

[0.3.0]: https://github.com/divyanshu-iitian/Agentic/releases/tag/v0.3.0
[0.2.0]: https://github.com/divyanshu-iitian/Agentic/releases/tag/v0.2.0
[0.1.0]: https://github.com/divyanshu-iitian/Agentic/releases/tag/v0.1.0
