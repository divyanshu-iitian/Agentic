---
name: code-review
description: Review code for correctness, clarity, regressions, and focused tests.
triggers:
  - review code
  - code review
  - find bugs
  - debug code
---

1. Inspect the relevant code and its callers before suggesting a change.
2. Prioritize concrete correctness bugs over style preferences.
3. Explain each finding with the affected behavior and evidence.
4. Propose the smallest safe fix that preserves public behavior.
5. Run the narrowest relevant test, then expand verification if risk warrants it.
6. Never claim a test passed unless its result was observed.
