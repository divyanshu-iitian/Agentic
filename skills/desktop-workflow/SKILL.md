---
name: desktop-workflow
description: Complete desktop workflows with semantic actions and visible verification.
triggers:
  - desktop
  - open app
  - vs code
  - create file
  - save file
---

1. Prefer semantic application and editor actions over coordinate clicks.
2. Use the latest visible UI state; do not assume a window has opened.
3. Enter text only after the intended field or editor is focused.
4. After every consequential action, verify a visible state change.
5. If the same action fails twice, change approach instead of repeating it.
6. Stop with `success: false` when the required target is unavailable or unsafe.
