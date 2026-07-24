"""Validation boundary between untrusted model output and executors."""

import re
from typing import Any
from urllib.parse import urlparse

from pydantic import ValidationError

from core.config import get_config
from execution.actions import parse_action
from utils.logger import log

SAFE_APP_NAME = re.compile(r"^[\w .+\-]{1,80}$", re.UNICODE)


class ActionValidator:
    """Validate action shape, bounds, allowlists, and URL protocols."""

    def __init__(self):
        config = get_config()
        self.whitelist_enabled = config.safety.enable_whitelist
        self.allowed_apps = [app.casefold() for app in config.safety.allowed_apps]
        self.allowed_domains = [
            domain.casefold().lstrip(".") for domain in config.safety.allowed_domains
        ]
        self.blocked_actions = set(config.safety.blocked_actions)
        log.info("Action validator initialized")

    def validate(self, action: str, args: dict[str, Any]) -> tuple[bool, str]:
        if action in self.blocked_actions:
            return self._reject(f"Action '{action}' is blocked for safety")

        try:
            parse_action({"action": action, "args": args})
        except (ValidationError, ValueError, TypeError) as exc:
            return self._reject(f"Invalid action payload: {exc}")

        if action == "open_app":
            return self._validate_open_app(args)
        if action == "browser_open":
            return self._validate_browser_url(args)
        return True, ""

    def _validate_open_app(self, args: dict[str, Any]) -> tuple[bool, str]:
        app_name = str(args.get("name", "")).strip().casefold()
        if not SAFE_APP_NAME.fullmatch(app_name):
            return self._reject("Application name contains unsafe characters")
        if self.whitelist_enabled and app_name not in self.allowed_apps:
            return self._reject(f"App '{app_name}' is not in the allowlist")
        return True, ""

    def _validate_browser_url(self, args: dict[str, Any]) -> tuple[bool, str]:
        raw_url = str(args.get("url", "")).strip()
        lowered = raw_url.casefold()
        if lowered.startswith(("javascript:", "file:", "data:", "vbscript:")):
            return self._reject("Only http and https URLs are allowed")
        parsed = urlparse(raw_url if "://" in raw_url else f"https://{raw_url}")
        if parsed.scheme not in {"http", "https"}:
            return self._reject("Only http and https URLs are allowed")

        hostname = (parsed.hostname or "").casefold()
        if not hostname:
            return self._reject("URL must include a valid hostname")

        if self.whitelist_enabled:
            allowed = any(
                hostname == domain or hostname.endswith(f".{domain}")
                for domain in self.allowed_domains
            )
            if not allowed:
                return self._reject(f"Domain is not in the allowlist: {hostname}")
        return True, ""

    @staticmethod
    def _reject(message: str) -> tuple[bool, str]:
        log.warning(message)
        return False, message
