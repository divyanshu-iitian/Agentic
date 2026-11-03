"""Provider-neutral chat messages, tool calls, and the provider interface."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

Role = Literal["system", "user", "assistant", "tool"]


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]
    id: str = field(default_factory=lambda: f"call_{uuid.uuid4().hex[:12]}")


@dataclass
class ImagePart:
    """A base64-encoded image attached to a message (screenshots, MCP images)."""

    data: str
    media_type: str = "image/png"


@dataclass
class Message:
    role: Role
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str | None = None
    name: str | None = None
    images: list[ImagePart] = field(default_factory=list)


@dataclass
class ToolSpec:
    """A tool as the model sees it: a name, a description, a JSON schema."""

    name: str
    description: str
    parameters: dict[str, Any]


@dataclass
class Completion:
    message: Message
    usage: dict[str, int] = field(default_factory=dict)


class Provider(Protocol):
    name: str
    model: str

    def complete(
        self,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
        temperature: float | None = None,
    ) -> Completion: ...


class ProviderError(RuntimeError):
    """A provider failed in a way the user can act on."""
