"""Wire-format tests for the Ollama, OpenAI-compatible, and Anthropic providers."""

import json

import pytest

from agentic.config import ProviderConfig
from agentic.llm.base import Message, ProviderError, ToolCall, ToolSpec
from agentic.llm.jsonutil import extract_json_object
from agentic.llm.providers import AnthropicProvider, OllamaProvider, OpenAICompatibleProvider

SPEC = ToolSpec("read_file", "Read a file", {"type": "object", "properties": {"path": {}}})
CONVERSATION = [
    Message("system", "be useful"),
    Message("user", "read a.txt and b.txt"),
    Message(
        "assistant",
        "",
        tool_calls=[
            ToolCall("read_file", {"path": "a.txt"}, id="c1"),
            ToolCall("read_file", {"path": "b.txt"}, id="c2"),
        ],
    ),
    Message("tool", "AAA", tool_call_id="c1", name="read_file"),
    Message("tool", "BBB", tool_call_id="c2", name="read_file"),
]


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload, self.status_code, self.text = payload, status, json.dumps(payload)

    def json(self):
        return self.payload


def capture(monkeypatch, provider, payload):
    sent = {}

    def fake_post(url, json, headers, timeout):
        sent.update(url=url, body=json, headers=headers)
        return FakeResponse(payload)

    monkeypatch.setattr(provider.session, "post", fake_post)
    return sent


def test_openai_compatible_round_trip(monkeypatch) -> None:
    monkeypatch.setenv("TEST_KEY", "secret")
    provider = OpenAICompatibleProvider(
        "groq",
        ProviderConfig(
            type="openai", model="m", api_key_env="TEST_KEY", base_url="https://api.example.com/v1"
        ),
    )
    sent = capture(
        monkeypatch,
        provider,
        {
            "choices": [
                {
                    "message": {
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "x9",
                                "function": {"name": "read_file", "arguments": '{"path": "c.txt"}'},
                            }
                        ],
                    }
                }
            ],
            "usage": {"prompt_tokens": 11, "completion_tokens": 3},
        },
    )

    completion = provider.complete(CONVERSATION, [SPEC])

    assert sent["url"] == "https://api.example.com/v1/chat/completions"
    assert sent["headers"]["Authorization"] == "Bearer secret"
    body = sent["body"]
    assert body["tools"][0]["function"]["name"] == "read_file"
    assistant = body["messages"][2]
    assert assistant["tool_calls"][0]["function"]["arguments"] == '{"path": "a.txt"}'
    assert body["messages"][3] == {"role": "tool", "tool_call_id": "c1", "content": "AAA"}
    call = completion.message.tool_calls[0]
    assert (call.id, call.name, call.arguments) == ("x9", "read_file", {"path": "c.txt"})
    assert completion.usage == {"input_tokens": 11, "output_tokens": 3}


def test_openai_requires_configured_key(monkeypatch) -> None:
    monkeypatch.delenv("MISSING_KEY", raising=False)
    provider = OpenAICompatibleProvider(
        "x", ProviderConfig(type="openai", model="m", api_key_env="MISSING_KEY")
    )
    with pytest.raises(ProviderError, match="MISSING_KEY"):
        provider.complete([Message("user", "hi")])


def test_anthropic_groups_tool_results_into_one_turn(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_TEST_KEY", "k")
    provider = AnthropicProvider(
        "claude",
        ProviderConfig(type="anthropic", model="claude-x", api_key_env="ANTHROPIC_TEST_KEY"),
    )
    sent = capture(
        monkeypatch,
        provider,
        {
            "content": [
                {"type": "text", "text": "Reading."},
                {"type": "tool_use", "id": "tu1", "name": "read_file", "input": {"path": "d"}},
            ],
            "usage": {"input_tokens": 5, "output_tokens": 2},
        },
    )

    completion = provider.complete([*CONVERSATION, Message("user", "and summarize")], [SPEC])

    body = sent["body"]
    assert sent["url"].endswith("/v1/messages")
    assert sent["headers"]["x-api-key"] == "k"
    assert body["system"] == "be useful"
    assert body["tools"][0]["input_schema"] == SPEC.parameters
    roles = [m["role"] for m in body["messages"]]
    assert roles == ["user", "assistant", "user"]
    results = body["messages"][2]["content"]
    assert [b["type"] for b in results] == ["tool_result", "tool_result", "text"]
    assert results[1] == {"type": "tool_result", "tool_use_id": "c2", "content": "BBB"}
    assert completion.message.content == "Reading."
    assert completion.message.tool_calls[0].id == "tu1"


def test_ollama_parses_dict_arguments(monkeypatch) -> None:
    provider = OllamaProvider("local", ProviderConfig())
    sent = capture(
        monkeypatch,
        provider,
        {
            "message": {
                "content": "",
                "tool_calls": [{"function": {"name": "read_file", "arguments": {"path": "e"}}}],
            },
            "prompt_eval_count": 7,
            "eval_count": 2,
        },
    )

    completion = provider.complete(CONVERSATION, [SPEC])

    assert sent["url"] == "http://127.0.0.1:11434/api/chat"
    assert sent["body"]["messages"][3]["tool_name"] == "read_file"
    assert sent["body"]["options"]["num_ctx"] == 16_384
    assert completion.message.tool_calls[0].arguments == {"path": "e"}
    assert completion.usage == {"input_tokens": 7, "output_tokens": 2}


def test_http_errors_become_provider_errors(monkeypatch) -> None:
    provider = OllamaProvider("local", ProviderConfig())
    monkeypatch.setattr(
        provider.session, "post", lambda *a, **k: FakeResponse({"error": "model not found"}, 404)
    )
    with pytest.raises(ProviderError, match="HTTP 404"):
        provider.complete([Message("user", "hi")])


def test_extract_json_object_handles_noise_and_braces_in_strings() -> None:
    text = 'Here you go: {"tasks": [{"task": "use {braces} here"}]} trailing } junk'
    assert extract_json_object(text, "tasks") == {"tasks": [{"task": "use {braces} here"}]}
    assert extract_json_object("no json", "tasks") is None
    assert extract_json_object('{"a": 1} {"tasks": []}', "tasks") == {"tasks": []}
