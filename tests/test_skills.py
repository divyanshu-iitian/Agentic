"""Tests for task-selected instruction skills."""

from pathlib import Path

from core.skills import SkillRegistry


def test_registry_selects_only_matching_skills(tmp_path: Path) -> None:
    skill_dir = tmp_path / "code-review"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: code-review
description: Review code.
triggers:
  - review code
---

Inspect callers first.
""",
        encoding="utf-8",
    )

    registry = SkillRegistry(tmp_path)

    assert [skill.name for skill in registry.select("Please review code")] == ["code-review"]
    assert registry.select("Open the calculator") == ()


def test_prompt_includes_instructions(tmp_path: Path) -> None:
    skill_dir = tmp_path / "research"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: research
description: Research carefully.
triggers:
  - investigate
---

Prefer primary sources.
""",
        encoding="utf-8",
    )

    prompt = SkillRegistry(tmp_path).prompt_for("Investigate this topic")

    assert "SKILL: research" in prompt
    assert "Prefer primary sources." in prompt


def test_registry_prefers_the_most_specific_trigger(tmp_path: Path) -> None:
    for name, trigger in [("generic", "code"), ("specific", "review code")]:
        skill_dir = tmp_path / name
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            f"""---
name: {name}
description: Test skill.
triggers:
  - {trigger}
---

Follow the test workflow.
""",
            encoding="utf-8",
        )

    selected = SkillRegistry(tmp_path).select("Please review code", limit=1)

    assert selected[0].name == "specific"


def test_trigger_matching_respects_word_boundaries(tmp_path: Path) -> None:
    skill_dir = tmp_path / "search"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: search
description: Search carefully.
triggers:
  - search
---

Use primary sources.
""",
        encoding="utf-8",
    )

    registry = SkillRegistry(tmp_path)

    assert registry.select("search for evidence")
    assert registry.select("researcher profile") == ()
