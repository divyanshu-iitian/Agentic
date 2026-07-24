"""Bounded, local long-term memory for explicit user feedback."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from utils.logger import log

MEMORY_FILE = Path(__file__).parent.parent / "agent_memory.json"
MAX_MEMORIES = 200
MAX_PROMPT_CHARS = 2_000
MAX_RELEVANT_MEMORIES = 3
WORD_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]{2,}", re.IGNORECASE)


def _keywords(text: str) -> set[str]:
    return {word.casefold() for word in WORD_PATTERN.findall(text)}


class LongTermMemory:
    """Store only user-approved feedback; never raw screens or model thoughts."""

    def __init__(self):
        self.memories: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if not MEMORY_FILE.exists():
            return
        try:
            payload = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
            if not isinstance(payload, list):
                raise ValueError("memory file must contain a list")
            self.memories = [
                item
                for item in payload[-MAX_MEMORIES:]
                if isinstance(item, dict)
                and isinstance(item.get("task"), str)
                and isinstance(item.get("feedback"), str)
            ]
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            log.error(f"Failed to load memory: {exc}")
            self.memories = []

    def save_feedback(self, task: str, feedback: str, steps_taken: list[str]) -> None:
        """Persist explicit feedback with deduplication and bounded retention."""
        task = task.strip()[:1_000]
        feedback = feedback.strip()[:2_000]
        if not task or not feedback:
            raise ValueError("task and feedback must not be empty")

        duplicate = any(
            item["task"].casefold() == task.casefold()
            and item["feedback"].casefold() == feedback.casefold()
            for item in self.memories
        )
        if duplicate:
            return

        self.memories.append(
            {
                "task": task,
                "feedback": feedback,
                "steps": [str(step)[:100] for step in steps_taken[-30:]],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        self.memories = self.memories[-MAX_MEMORIES:]
        self._persist()
        log.info("Saved explicit user feedback")

    def _persist(self) -> None:
        MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        temporary = MEMORY_FILE.with_suffix(f"{MEMORY_FILE.suffix}.tmp")
        temporary.write_text(
            json.dumps(self.memories, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temporary.replace(MEMORY_FILE)

    def get_relevant_feedback(self, current_task: str) -> str:
        """Retrieve a tiny, deterministic set of lexically relevant memories."""
        task_words = _keywords(current_task)
        if not task_words:
            return ""

        ranked: list[tuple[float, str, dict[str, Any]]] = []
        for memory in self.memories:
            memory_words = _keywords(memory["task"])
            overlap = task_words & memory_words
            if not overlap:
                continue
            score = len(overlap) / max(1, len(task_words | memory_words))
            ranked.append((score, str(memory.get("timestamp", "")), memory))

        ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
        tips = [
            f"- For a similar task ({memory['task']}), the user said: {memory['feedback']}"
            for _, _, memory in ranked[:MAX_RELEVANT_MEMORIES]
        ]
        return "\n".join(tips)[:MAX_PROMPT_CHARS]
