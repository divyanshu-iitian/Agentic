# Architecture

Agentic currently has two user surfaces sharing the same local-first direction.

## Lightweight chat

```text
React UI
   |
   | HTTP on localhost
   v
FastAPI runtime
   |
   +-- Ollama (default)
   +-- Groq (optional)
   +-- Edge TTS (optional)
```

The browser UI intentionally avoids WebGL and continuous animation. The API
binds to `127.0.0.1`, restricts CORS to local development origins, validates
message sizes, limits conversation history, and keeps voice generation off by
default.

## Desktop automation

```text
Task
  |
  v
Observe -> Reason -> Validate -> Execute -> Verify
  |          |           |          |
  |          |           |          +-- desktop and browser adapters
  |          |           +-- allowlists, blocked actions, action limit
  |          +-- local Ollama model plus relevant skills
  +-- screen capture, OCR, and symbolic UI state
```

The desktop agent uses strictly typed JSON actions. The language model cannot
call arbitrary Python functions directly. Unknown tools, extra arguments,
unsafe URL protocols, values outside action bounds, and disallowed targets are
rejected before execution. `Ctrl + Alt + Q` provides an emergency stop.

## Context and memory

```text
current observation       short-lived, compact symbolic state
recent trajectory         last five action outcomes
failure reflections       last three task-local recovery notes
explicit user feedback    bounded local JSON, selected by relevance
skills                    at most two task-relevant Markdown files
```

This tiering keeps prompts useful for small context windows. Raw screenshots,
hidden reasoning, and model-generated reflections are not written to long-term
memory. Only explicit user feedback persists.

## Trust boundary

The user task is authoritative. OCR, DOM summaries, webpage text, and extracted
content are untrusted environment data. Prompt guidance reinforces that
boundary, while typed schemas, allowlists, action budgets, and narrow executors
enforce it in code.

## Skills

Skills live under `skills/<name>/SKILL.md`. They contain YAML metadata and
Markdown instructions. The registry:

1. discovers valid skill files at startup
2. matches task text against declared triggers
3. selects at most two skills
4. caps combined skill prompt content at 6,000 characters

Skills are instructions only. They do not execute setup scripts or bypass the
action validator.

## Boundaries

- `core/`: orchestration, state, memory, planning, and skills
- `llm/`: local model client, prompts, and response parsing
- `perception/`: screen observation, OCR, and change detection
- `execution/`: desktop and browser action adapters
- `planning/`: action validation
- `safety/`: kill switch and action limits
- `ui/`: classic desktop command surface
- `agentic-app/`: lightweight React and FastAPI chat

The two surfaces are intentionally separate until a permission-aware unified
runtime is ready.

The research-to-implementation rationale is documented in
[research foundations](research-foundations.md).
