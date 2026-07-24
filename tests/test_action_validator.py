"""Tests for action validation boundaries."""

from planning.action_validator import ActionValidator


def test_domain_whitelist_rejects_substring_spoofing() -> None:
    validator = ActionValidator()
    validator.whitelist_enabled = True
    validator.allowed_domains = ["github.com"]

    valid, _ = validator.validate(
        "browser_open",
        {"url": "https://github.com/openai"},
    )
    spoofed, _ = validator.validate(
        "browser_open",
        {"url": "https://example.com/?next=github.com"},
    )

    assert valid is True
    assert spoofed is False
