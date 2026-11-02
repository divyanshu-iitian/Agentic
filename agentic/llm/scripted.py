"""A deterministic provider for tests and offline demos of the control flow."""

from __future__ import annotations

import threading
from collections.abc import Callable

from agentic.llm.base import Completion, Message, ToolCall, ToolSpec

Responder = Callable[[list[Message], list[ToolSpec] | None], Message | str]


class ScriptedProvider:
    """Replays queued replies, or delegates each turn to a responder function."""

    def __init__(
        self,
        replies: list[Message | str] | None = None,
        responder: Responder | None = None,
        name: str = "scripted",
    ):
        self.name = name
        self.model = "scripted"
        self.replies = list(replies or [])
        self.responder = responder
        self.calls: list[list[Message]] = []
        self._lock = threading.Lock()

    def complete(self, messages, tools=None, temperature=None) -> Completion:
        with self._lock:
            self.calls.append(list(messages))
            if self.responder is None:
                reply = self.replies.pop(0) if self.replies else "done"
        if self.responder is not None:
            # Not under the lock: concurrent heads must be able to overlap.
            reply = self.responder(messages, tools)
        if isinstance(reply, str):
            reply = Message("assistant", reply)
        return Completion(reply, {"input_tokens": 0, "output_tokens": 0})


def tool_reply(name: str, **arguments) -> Message:
    return Message("assistant", "", tool_calls=[ToolCall(name=name, arguments=arguments)])
