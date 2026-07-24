"""Tests for the lightweight local API without starting a server."""

import importlib.util
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError


def _load_api_module():
    path = Path(__file__).parents[1] / "agentic-app" / "backend" / "main.py"
    spec = importlib.util.spec_from_file_location("agentic_backend", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_chat_history_is_bounded() -> None:
    api = _load_api_module()
    history = [{"role": "user", "content": "hello"}] * (api.MAX_HISTORY_MESSAGES + 1)

    with pytest.raises(ValidationError):
        api.ChatRequest(message="test", history=history)


def test_ollama_request_uses_low_resource_limits(monkeypatch) -> None:
    api = _load_api_module()
    captured = {}

    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"message": {"content": "Local response"}}

    def fake_post(url, json, timeout):
        captured.update(url=url, payload=json, timeout=timeout)
        return Response()

    monkeypatch.setattr(api.ollama_session, "post", fake_post)
    result = api._chat_with_ollama(api.ChatRequest(message="hello"))

    assert result == "Local response"
    assert captured["payload"]["options"]["num_ctx"] == 4096
    assert captured["payload"]["options"]["num_predict"] == 768
    assert captured["timeout"] == 120
