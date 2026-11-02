"""Compatibility shim: the skill registry now lives in agentic.skills."""

from agentic.skills import DEFAULT_SKILLS_DIR, MAX_SKILL_PROMPT_CHARS, Skill, SkillRegistry

__all__ = ["DEFAULT_SKILLS_DIR", "MAX_SKILL_PROMPT_CHARS", "Skill", "SkillRegistry"]
