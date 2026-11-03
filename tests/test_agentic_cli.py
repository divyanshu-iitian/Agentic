"""Smoke tests for the command line interface."""

import pytest

from agentic.cli import main
from agentic.config import load_settings


def test_version(capsys) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])
    assert exit_info.value.code == 0
    assert "agentic 0.3.0" in capsys.readouterr().out


def test_init_heads_memory_and_schedule(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["init"]) == 0
    settings = load_settings(tmp_path / "agentic.yaml")
    assert settings.permissions.write == "ask" and settings.workspace_path.is_dir()

    assert main(["heads"]) == 0
    out = capsys.readouterr().out
    assert "researcher" in out and "built-in" in out

    assert main(["memory", "add", "Prefers", "metric", "units"]) == 0
    assert main(["memory", "search", "units"]) == 0
    assert "Prefers metric units" in capsys.readouterr().out

    assert main(["schedule", "add", "check", "inbox", "--every", "30"]) == 0
    assert main(["schedule", "list"]) == 0
    assert "every 30m" in capsys.readouterr().out
    assert main(["schedule", "add", "bad", "--cron", "nope"]) == 2


def test_unknown_provider_is_a_clean_error(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["run", "hello", "--provider", "missing"]) == 2
    assert "Unknown provider" in capsys.readouterr().err


def test_custom_heads_override_builtins(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "heads").mkdir()
    (tmp_path / "heads" / "researcher.md").write_text(
        "---\nname: researcher\ndescription: My own researcher\ntools: [http_fetch]\n---\nHi\n",
        encoding="utf-8",
    )
    assert main(["heads"]) == 0
    assert "My own researcher" in capsys.readouterr().out
