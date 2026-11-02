"""Heads: specialist agent profiles defined as Markdown with YAML front matter.

Built-in heads ship in agentic/profiles/. A file with the same name in the
project's heads/ directory overrides a built-in head; a new name adds one.

    ---
    name: researcher
    description: Finds and verifies information on the web.
    tools: [web_search, http_fetch, recall]
    provider: local        # optional, any key under `providers`
    max_steps: 10          # optional
    temperature: 0.3       # optional
    ---
    System prompt for this head.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

BUILTIN_DIR = Path(__file__).resolve().parent / "profiles"
VALID_NAME = re.compile(r"^[a-z][a-z0-9_-]{0,39}$")
log = logging.getLogger("agentic.heads")


@dataclass(frozen=True)
class HeadProfile:
    name: str
    description: str
    system_prompt: str
    tools: tuple[str, ...] = field(default_factory=tuple)
    provider: str | None = None
    max_steps: int | None = None
    temperature: float | None = None
    path: Path | None = None


def parse_head(path: Path) -> HeadProfile:
    raw = path.read_text(encoding="utf-8").strip()
    parts = raw.split("---", 2)
    if not raw.startswith("---") or len(parts) != 3:
        raise ValueError("a head needs YAML front matter between --- lines")
    meta = yaml.safe_load(parts[1]) or {}
    name = str(meta.get("name", "")).strip()
    if not VALID_NAME.fullmatch(name):
        raise ValueError(f"invalid head name {name!r}")
    tools = meta.get("tools", [])
    if not isinstance(tools, list):
        raise ValueError("tools must be a YAML list")
    prompt = parts[2].strip()
    if not prompt:
        raise ValueError("a head needs a system prompt")
    return HeadProfile(
        name=name,
        description=str(meta.get("description", "")).strip(),
        system_prompt=prompt,
        tools=tuple(str(tool) for tool in tools),
        provider=meta.get("provider"),
        max_steps=int(meta["max_steps"]) if meta.get("max_steps") else None,
        temperature=float(meta["temperature"]) if meta.get("temperature") is not None else None,
        path=path,
    )


def load_heads(extra_dir: Path | None = None) -> dict[str, HeadProfile]:
    heads: dict[str, HeadProfile] = {}
    for directory in (BUILTIN_DIR, extra_dir):
        if directory is None or not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.md")):
            try:
                head = parse_head(path)
            except (OSError, ValueError, yaml.YAMLError) as exc:
                log.warning("Skipping head %s: %s", path, exc)
                continue
            heads[head.name] = head
    return heads
