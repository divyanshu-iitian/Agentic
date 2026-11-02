"""Extract JSON objects from free-form model text."""

from __future__ import annotations

import json
import re
from typing import Any

FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def _balanced_objects(text: str):
    """Yield every top-level {...} span, respecting strings and escapes."""
    depth = 0
    start = -1
    in_string = False
    escaped = False
    for index, char in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            if depth == 0:
                start = index
            depth += 1
        elif char == "}" and depth:
            depth -= 1
            if depth == 0:
                yield text[start : index + 1]


def extract_json_object(text: str, required_key: str | None = None) -> dict[str, Any] | None:
    """Return the first JSON object in text, optionally one containing a key."""
    if not text:
        return None
    candidates = [block for block in FENCE.findall(text)] + [text]
    for candidate in candidates:
        stripped = candidate.strip()
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, dict) and (required_key is None or required_key in parsed):
                return parsed
        except json.JSONDecodeError:
            pass
        for span in _balanced_objects(stripped):
            try:
                parsed = json.loads(span)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict) and (required_key is None or required_key in parsed):
                return parsed
    return None
