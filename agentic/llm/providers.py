"""Chat providers: Ollama, any OpenAI-compatible API, and Anthropic.

Each provider converts the neutral Message/ToolSpec types to its wire format
and back. Only `requests` is needed; no vendor SDK is imported.
"""

from __future__ import annotations

import json
from typing import Any

import requests

from agentic.config import ProviderConfig
from agentic.llm.base import Completion, Message, Provider, ProviderError, ToolCall, ToolSpec
from agentic.llm.jsonutil import extract_json_object

DEFAULT_BASE_URLS = {
    "ollama": "http://127.0.0.1:11434",
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com",
}
ANTHROPIC_VERSION = "2023-06-01"


def _parse_arguments(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = extract_json_object(raw)
        if isinstance(parsed, dict):
            return parsed
    return {}


class _HTTPProvider:
    def __init__(self, name: str, config: ProviderConfig):
        self.name = name
        self.config = config
        self.model = config.model
        self.base_url = (config.base_url or DEFAULT_BASE_URLS[config.type]).rstrip("/")
        self.session = requests.Session()

    def _post(self, url: str, payload: dict[str, Any], headers: dict[str, str] | None = None):
        try:
            response = self.session.post(
                url, json=payload, headers=headers or {}, timeout=self.config.timeout
            )
        except requests.ConnectionError as exc:
            raise ProviderError(f"{self.name}: cannot reach {self.base_url}") from exc
        except requests.Timeout as exc:
            raise ProviderError(
                f"{self.name}: timed out after {self.config.timeout}s; "
                "try a smaller model or raise the provider timeout"
            ) from exc
        if response.status_code >= 400:
            detail = response.text[:500]
            raise ProviderError(f"{self.name}: HTTP {response.status_code}: {detail}")
        return response.json()


class OllamaProvider(_HTTPProvider):
    """Local models through Ollama's /api/chat endpoint."""

    def complete(self, messages, tools=None, temperature=None) -> Completion:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [self._message(m) for m in messages],
            "stream": False,
            "options": {
                "temperature": self.config.temperature if temperature is None else temperature,
                "num_ctx": self.config.context_window,
                "num_predict": self.config.max_tokens,
            },
            "keep_alive": "10m",
        }
        if tools:
            payload["tools"] = [_openai_tool(tool) for tool in tools]
        data = self._post(f"{self.base_url}/api/chat", payload)
        raw = data.get("message", {})
        calls = [
            ToolCall(
                name=call.get("function", {}).get("name", ""),
                arguments=_parse_arguments(call.get("function", {}).get("arguments")),
            )
            for call in raw.get("tool_calls") or []
        ]
        usage = {
            "input_tokens": int(data.get("prompt_eval_count") or 0),
            "output_tokens": int(data.get("eval_count") or 0),
        }
        return Completion(
            Message("assistant", (raw.get("content") or "").strip(), tool_calls=calls), usage
        )

    @staticmethod
    def _message(message: Message) -> dict[str, Any]:
        payload: dict[str, Any] = {"role": message.role, "content": message.content}
        if message.tool_calls:
            payload["tool_calls"] = [
                {"function": {"name": call.name, "arguments": call.arguments}}
                for call in message.tool_calls
            ]
        if message.role == "tool" and message.name:
            payload["tool_name"] = message.name
        return payload

    def health(self) -> bool:
        try:
            return self.session.get(f"{self.base_url}/api/tags", timeout=3).ok
        except requests.RequestException:
            return False


class OpenAICompatibleProvider(_HTTPProvider):
    """OpenAI, Groq, OpenRouter, LM Studio, vLLM, and other compatible APIs."""

    def complete(self, messages, tools=None, temperature=None) -> Completion:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [self._message(m) for m in messages],
            "temperature": self.config.temperature if temperature is None else temperature,
            "max_tokens": self.config.max_tokens,
        }
        if tools:
            payload["tools"] = [_openai_tool(tool) for tool in tools]
        headers = {}
        key = self.config.api_key()
        if key:
            headers["Authorization"] = f"Bearer {key}"
        elif self.config.api_key_env:
            raise ProviderError(f"{self.name}: set the {self.config.api_key_env} variable")

        data = self._post(f"{self.base_url}/chat/completions", payload, headers)
        choices = data.get("choices") or []
        if not choices:
            raise ProviderError(f"{self.name}: response contained no choices")
        raw = choices[0].get("message", {})
        calls = [
            ToolCall(
                id=call.get("id") or ToolCall("", {}).id,
                name=call.get("function", {}).get("name", ""),
                arguments=_parse_arguments(call.get("function", {}).get("arguments")),
            )
            for call in raw.get("tool_calls") or []
        ]
        usage = data.get("usage") or {}
        return Completion(
            Message("assistant", (raw.get("content") or "").strip(), tool_calls=calls),
            {
                "input_tokens": int(usage.get("prompt_tokens") or 0),
                "output_tokens": int(usage.get("completion_tokens") or 0),
            },
        )

    @staticmethod
    def _message(message: Message) -> dict[str, Any]:
        if message.role == "tool":
            return {
                "role": "tool",
                "tool_call_id": message.tool_call_id,
                "content": message.content,
            }
        payload: dict[str, Any] = {"role": message.role, "content": message.content}
        if message.tool_calls:
            payload["content"] = message.content or None
            payload["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.name, "arguments": json.dumps(call.arguments)},
                }
                for call in message.tool_calls
            ]
        return payload


class AnthropicProvider(_HTTPProvider):
    """Claude models through the Anthropic Messages API."""

    def complete(self, messages, tools=None, temperature=None) -> Completion:
        key = self.config.api_key()
        if not key:
            raise ProviderError(
                f"{self.name}: set the {self.config.api_key_env or 'ANTHROPIC_API_KEY'} variable"
            )
        system = "\n\n".join(m.content for m in messages if m.role == "system")
        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature if temperature is None else temperature,
            "messages": self._messages([m for m in messages if m.role != "system"]),
        }
        if system:
            payload["system"] = system
        if tools:
            payload["tools"] = [
                {"name": t.name, "description": t.description, "input_schema": t.parameters}
                for t in tools
            ]
        data = self._post(
            f"{self.base_url}/v1/messages",
            payload,
            {"x-api-key": key, "anthropic-version": ANTHROPIC_VERSION},
        )
        text_parts: list[str] = []
        calls: list[ToolCall] = []
        for block in data.get("content") or []:
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                calls.append(
                    ToolCall(id=block["id"], name=block["name"], arguments=block.get("input") or {})
                )
        usage = data.get("usage") or {}
        return Completion(
            Message("assistant", "".join(text_parts).strip(), tool_calls=calls),
            {
                "input_tokens": int(usage.get("input_tokens") or 0),
                "output_tokens": int(usage.get("output_tokens") or 0),
            },
        )

    @staticmethod
    def _messages(messages: list[Message]) -> list[dict[str, Any]]:
        """Convert to alternating turns; consecutive tool results share one turn."""
        converted: list[dict[str, Any]] = []
        for message in messages:
            if message.role == "tool":
                block = {
                    "type": "tool_result",
                    "tool_use_id": message.tool_call_id,
                    "content": message.content,
                }
                previous = converted[-1] if converted else None
                if (
                    previous
                    and previous["role"] == "user"
                    and isinstance(previous["content"], list)
                    and previous["content"]
                    and previous["content"][0].get("type") == "tool_result"
                ):
                    previous["content"].append(block)
                else:
                    converted.append({"role": "user", "content": [block]})
            elif message.role == "assistant" and message.tool_calls:
                content: list[dict[str, Any]] = []
                if message.content:
                    content.append({"type": "text", "text": message.content})
                content.extend(
                    {"type": "tool_use", "id": c.id, "name": c.name, "input": c.arguments}
                    for c in message.tool_calls
                )
                converted.append({"role": "assistant", "content": content})
            elif converted and converted[-1]["role"] == message.role:
                # The API expects alternating turns; fold same-role text together.
                previous = converted[-1]
                if isinstance(previous["content"], str):
                    previous["content"] = [{"type": "text", "text": previous["content"]}]
                previous["content"].append({"type": "text", "text": message.content or "(empty)"})
            else:
                converted.append({"role": message.role, "content": message.content or "(empty)"})
        return converted


def _openai_tool(tool: ToolSpec) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
        },
    }


class PromptToolProvider:
    """Tool calling for models without a native tool API.

    Tools are described in the system prompt and the model answers with a JSON
    object. Tool results come back as user turns.
    """

    def __init__(self, inner: Provider):
        self.inner = inner
        self.name = inner.name
        self.model = inner.model

    def complete(self, messages, tools=None, temperature=None) -> Completion:
        if not tools:
            return self.inner.complete(self._flatten(messages), None, temperature)

        catalogue = "\n".join(
            f"- {t.name}: {t.description}\n  args schema: {json.dumps(t.parameters)}" for t in tools
        )
        protocol = (
            "\n\nTOOLS\nYou can call one tool per reply. To call a tool, reply with ONLY:\n"
            '{"tool": "<name>", "args": {...}}\n'
            "When the task is complete, reply with your final answer as plain text "
            "(no JSON tool object).\n\nAvailable tools:\n" + catalogue
        )
        flattened = self._flatten(messages)
        if flattened and flattened[0].role == "system":
            flattened[0] = Message("system", flattened[0].content + protocol)
        else:
            flattened.insert(0, Message("system", protocol.strip()))

        completion = self.inner.complete(flattened, None, temperature)
        call = extract_json_object(completion.message.content, required_key="tool")
        known = {t.name for t in tools}
        if call and isinstance(call.get("tool"), str) and call["tool"] in known:
            args = call.get("args") if isinstance(call.get("args"), dict) else {}
            completion.message = Message(
                "assistant", "", tool_calls=[ToolCall(name=call["tool"], arguments=args)]
            )
        return completion

    @staticmethod
    def _flatten(messages: list[Message]) -> list[Message]:
        flattened: list[Message] = []
        for message in messages:
            if message.role == "tool":
                flattened.append(
                    Message("user", f"TOOL RESULT ({message.name}):\n{message.content}")
                )
            elif message.role == "assistant" and message.tool_calls:
                call = message.tool_calls[0]
                flattened.append(
                    Message("assistant", json.dumps({"tool": call.name, "args": call.arguments}))
                )
            else:
                flattened.append(Message(message.role, message.content))
        return flattened


def build_provider(name: str, config: ProviderConfig) -> Provider:
    classes = {
        "ollama": OllamaProvider,
        "openai": OpenAICompatibleProvider,
        "anthropic": AnthropicProvider,
    }
    provider: Provider = classes[config.type](name, config)
    if config.tool_mode == "prompt":
        provider = PromptToolProvider(provider)
    return provider
