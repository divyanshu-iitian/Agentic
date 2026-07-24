"""
JSON Parser

Robust parsing of LLM outputs to extract valid JSON actions.
"""

import json
import re
from typing import Any

from utils.logger import log


class JSONParser:
    """Parse and extract JSON from LLM outputs"""

    @staticmethod
    def extract_json(text: str) -> dict[str, Any] | None:
        """
        Extract first valid JSON object from text.

        Handles:
        - Pure JSON
        - JSON wrapped in markdown
        - JSON with surrounding text
        - Malformed JSON (attempts repair)

        Args:
            text: Raw LLM output

        Returns:
            Parsed JSON dict or None
        """
        # Remove markdown code blocks
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*", "", text)

        # Try direct parse first
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass

        # Try to find JSON pattern
        json_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
        matches = re.finditer(json_pattern, text, re.DOTALL)

        for match in matches:
            try:
                candidate = match.group(0)
                parsed = json.loads(candidate)
                if isinstance(parsed, dict) and "action" in parsed:
                    return parsed
            except json.JSONDecodeError:
                continue

        # Try more aggressive extraction
        try:
            # Find outermost braces
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                candidate = text[start : end + 1]
                return json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            pass

        log.warning(f"Failed to extract JSON from: {text[:100]}...")
        return None

    @staticmethod
    def validate_action_json(data: dict[str, Any]) -> bool:
        """
        Validate if JSON has required action structure.

        Args:
            data: Parsed JSON

        Returns:
            True if valid action format
        """
        if not isinstance(data, dict):
            return False

        if "action" not in data:
            log.warning("JSON missing 'action' field")
            return False

        if "args" not in data:
            log.warning("JSON missing 'args' field")
            return False

        return True

    @staticmethod
    def parse_llm_output(text: str) -> dict[str, Any] | None:
        """
        Full parsing pipeline: extract + validate.

        Args:
            text: Raw LLM output

        Returns:
            Validated action JSON or None
        """
        json_data = JSONParser.extract_json(text)

        if json_data is None:
            return None

        if not JSONParser.validate_action_json(json_data):
            return None

        log.info(f"Parsed action: {json_data['action']}")
        return json_data
