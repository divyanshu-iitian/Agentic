"""Small, safe skill registry for local models.

Skills are Markdown instructions, not executable plugins. Only skills relevant
to the current task are included in the prompt so small context windows remain
useful on low-resource machines.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULT_SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"
MAX_SKILL_PROMPT_CHARS = 6_000
log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    triggers: tuple[str, ...]
    instructions: str
    path: Path

    def matches(self, task: str) -> bool:
        normalized_task = task.casefold()
        return any(trigger.casefold() in normalized_task for trigger in self.triggers)


class SkillRegistry:
    """Discover SKILL.md files and select task-relevant instructions."""

    def __init__(self, skills_dir: Path = DEFAULT_SKILLS_DIR):
        self.skills_dir = skills_dir
        self.skills = self._discover()

    def _discover(self) -> tuple[Skill, ...]:
        if not self.skills_dir.exists():
            return ()

        discovered: list[Skill] = []
        for path in sorted(self.skills_dir.glob("*/SKILL.md")):
            try:
                skill = self._load_skill(path)
                if skill:
                    discovered.append(skill)
            except (OSError, ValueError, yaml.YAMLError) as exc:
                log.warning(f"Skipping invalid skill at {path}: {exc}")

        log.info(f"Loaded {len(discovered)} instruction skills")
        return tuple(discovered)

    @staticmethod
    def _load_skill(path: Path) -> Skill | None:
        raw = path.read_text(encoding="utf-8").strip()
        if not raw.startswith("---"):
            raise ValueError("missing YAML front matter")

        parts = raw.split("---", 2)
        if len(parts) != 3:
            raise ValueError("front matter must end with ---")

        metadata: dict[str, Any] = yaml.safe_load(parts[1]) or {}
        name = str(metadata.get("name", "")).strip()
        description = str(metadata.get("description", "")).strip()
        triggers_value = metadata.get("triggers", [])
        instructions = parts[2].strip()

        if not name or not description or not instructions:
            raise ValueError("name, description, and instructions are required")
        if not isinstance(triggers_value, list):
            raise ValueError("triggers must be a YAML list")

        triggers = tuple(str(trigger).strip() for trigger in triggers_value if str(trigger).strip())
        if not triggers:
            raise ValueError("at least one trigger is required")

        return Skill(
            name=name,
            description=description,
            triggers=triggers,
            instructions=instructions,
            path=path,
        )

    def select(self, task: str, limit: int = 2) -> tuple[Skill, ...]:
        """Return a small deterministic set of skills relevant to a task."""
        return tuple(skill for skill in self.skills if skill.matches(task))[:limit]

    def prompt_for(self, task: str) -> str:
        selected = self.select(task)
        if not selected:
            return ""

        sections = ["\nRELEVANT SKILLS:"]
        used_chars = len(sections[0])
        for skill in selected:
            section = (
                f"\n\nSKILL: {skill.name}\n"
                f"PURPOSE: {skill.description}\n"
                f"INSTRUCTIONS:\n{skill.instructions}"
            )
            remaining = MAX_SKILL_PROMPT_CHARS - used_chars
            if remaining <= 0:
                break
            sections.append(section[:remaining])
            used_chars += min(len(section), remaining)

        return "".join(sections)
