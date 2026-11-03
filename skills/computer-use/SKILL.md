---
name: computer-use
description: Operate desktop applications reliably step by step.
triggers:
  - desktop
  - window
  - application
  - notepad
  - calculator
  - file explorer
  - windows settings
  - computer use
---

1. Find the target window: `desktop_windows`, then `desktop_window` to focus it.
2. Read its controls with `desktop_ui_tree` before clicking anything.
3. Prefer keyboard shortcuts, then `desktop_click_element` by [id].
4. After each action, read the ui tree (or a screenshot) again to confirm the change.
5. When typing into a field, pass its [id] as `element` so it is clicked first.
6. Stop and report if a dialog asks for credentials, payment, or deletion.
