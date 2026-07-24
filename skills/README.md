# Agentic skills

Skills teach the local model a focused workflow without adding Python code or
expanding the always-on system prompt. The runtime loads at most two matching
skills for a task, keeping small models responsive.

## Add a skill

Create `skills/<skill-name>/SKILL.md`:

```md
---
name: clear-skill-name
description: One sentence describing when this workflow helps.
triggers:
  - keyword
  - short phrase
---

Write short, ordered instructions here. Prefer verifiable steps. Tell the agent
when to stop and ask for confirmation before destructive or irreversible work.
```

Skills are prompt instructions only. They cannot import packages, run setup
scripts, or bypass the action validator. Review community skills before adding
them to a trusted installation.
