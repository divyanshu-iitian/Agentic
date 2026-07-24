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


def test_validator_rejects_unknown_actions_and_extra_arguments() -> None:
    validator = ActionValidator()

    unknown, _ = validator.validate("run_shell", {"command": "whoami"})
    extra, _ = validator.validate("click", {"x": 10, "y": 20, "command": "whoami"})

    assert unknown is False
    assert extra is False


def test_validator_rejects_unsafe_url_protocols() -> None:
    validator = ActionValidator()
    validator.whitelist_enabled = False

    valid, _ = validator.validate("browser_open", {"url": "https://example.com"})
    javascript, _ = validator.validate("browser_open", {"url": "javascript:alert(1)"})
    file_url, _ = validator.validate("browser_open", {"url": "file:///etc/passwd"})

    assert valid is True
    assert javascript is False
    assert file_url is False


def test_validator_enforces_numeric_bounds() -> None:
    validator = ActionValidator()

    valid, _ = validator.validate("wait", {"seconds": 2})
    too_long, _ = validator.validate("wait", {"seconds": 300})
    negative_click, _ = validator.validate("click", {"x": -1, "y": 20})

    assert valid is True
    assert too_long is False
    assert negative_click is False


def test_stop_can_report_a_blocker() -> None:
    validator = ActionValidator()

    valid, _ = validator.validate(
        "stop",
        {"success": False, "reason": "The requested application is unavailable."},
    )

    assert valid is True
