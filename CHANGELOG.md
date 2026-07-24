# Changelog

All notable changes are recorded here. Agentic follows semantic versioning.

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

[0.1.0]: https://github.com/divyanshu-iitian/Agentic/releases/tag/v0.1.0
