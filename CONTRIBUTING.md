# Contributing to Agentic

Thanks for helping make local AI practical on ordinary computers.

## Good first contributions

- reduce startup time, memory use, or install size
- add focused tests for an existing behavior
- improve keyboard navigation, contrast, or screen reader support
- document a reproducible hardware benchmark
- add a narrow instruction skill with clear triggers

## Before opening a pull request

1. Keep the change focused. Explain the user problem it solves.
2. Do not commit secrets, model files, generated audio, screenshots, or logs.
3. Add or update tests for behavior changes.
4. Run the relevant checks:

```powershell
python -m pytest test_skills.py
python -m compileall core antigravity-chat\backend

cd antigravity-chat\frontend
npm run lint
npm run build
```

5. Include before and after memory or bundle measurements for performance work.
6. Explain privacy and permission effects for new automation capabilities.

## Skills

Skills must be Markdown instructions only. Keep them short enough for small
models, use specific triggers, require verification, and request confirmation
before destructive or irreversible actions. Never include instructions to
download and execute unreviewed code.

## Pull request checklist

- [ ] The change works without a cloud API unless the feature is explicitly optional.
- [ ] Error, empty, loading, and offline states remain usable.
- [ ] Keyboard navigation and reduced-motion behavior still work.
- [ ] No consequential action became silent or implicit.
- [ ] Documentation matches the implementation.
