"""Tool registry: typed arguments, permission tiers, approvals, and timeouts.

A tool is a JSON-schema description plus a handler. The model only ever sees
the description; every call is validated against the schema, checked against
the approval policy, run with a timeout, and truncated before it re-enters
the context window.
"""

from __future__ import annotations

import asyncio
import fnmatch
import inspect
import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from agentic.approvals import ApprovalGate, ApprovalRequest
from agentic.llm.base import ToolSpec

if TYPE_CHECKING:
    from agentic.runtime import Runtime

PERMISSIONS = ("read", "memory", "network", "write", "execute", "schedule", "desktop")
Handler = Callable[[dict[str, Any], "ToolContext"], Awaitable[str] | str]


class ToolError(Exception):
    """A tool failed in an expected way; the message is shown to the model."""


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    permission: str
    handler: Handler
    # Blocking handlers run in a worker thread so heads stay concurrent.
    blocking: bool = True
    # Overrides limits.tool_timeout for tools that enforce their own limit.
    timeout: float | None = None

    def __post_init__(self) -> None:
        if self.permission not in PERMISSIONS:
            raise ValueError(f"{self.name}: unknown permission {self.permission!r}")

    def spec(self) -> ToolSpec:
        return ToolSpec(self.name, self.description, self.parameters)


@dataclass
class ToolContext:
    runtime: Runtime
    run_id: str
    agent: str
    origin: str = "cli"
    depth: int = 0
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def workspace(self) -> Path:
        return self.runtime.settings.workspace_path


@dataclass
class ToolResult:
    ok: bool
    content: str
    duration: float = 0.0


def schema(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": False,
    }


_JSON_TYPES: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool,),
    "array": (list,),
    "object": (dict,),
}


def validate_args(parameters: dict[str, Any], args: Any) -> dict[str, Any]:
    """Check arguments against the subset of JSON schema the tools use."""
    if not isinstance(args, dict):
        raise ToolError("arguments must be a JSON object")
    properties: dict[str, Any] = parameters.get("properties", {})
    for key in parameters.get("required", []):
        if key not in args:
            raise ToolError(f"missing required argument '{key}'")
    if parameters.get("additionalProperties") is False:
        unknown = sorted(set(args) - set(properties))
        if unknown:
            raise ToolError(f"unknown argument(s): {', '.join(unknown)}")
    cleaned: dict[str, Any] = {}
    for key, value in args.items():
        prop = properties.get(key, {})
        expected = prop.get("type")
        if isinstance(expected, str) and expected in _JSON_TYPES:
            types = _JSON_TYPES[expected]
            if isinstance(value, bool) and bool not in types:
                raise ToolError(f"argument '{key}' must be {expected}")
            if expected == "integer" and isinstance(value, float) and value.is_integer():
                value = int(value)
            if not isinstance(value, types):
                raise ToolError(f"argument '{key}' must be {expected}")
        if "enum" in prop and value not in prop["enum"]:
            raise ToolError(f"argument '{key}' must be one of {prop['enum']}")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if "minimum" in prop and value < prop["minimum"]:
                raise ToolError(f"argument '{key}' must be >= {prop['minimum']}")
            if "maximum" in prop and value > prop["maximum"]:
                raise ToolError(f"argument '{key}' must be <= {prop['maximum']}")
        if isinstance(value, str) and "maxLength" in prop and len(value) > prop["maxLength"]:
            raise ToolError(f"argument '{key}' exceeds {prop['maxLength']} characters")
        cleaned[key] = value
    return cleaned


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    head = limit * 3 // 4
    tail = limit - head
    return f"{text[:head]}\n... [{len(text) - limit} characters truncated] ...\n{text[-tail:]}"


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool {tool.name!r} is already registered")
        self._tools[tool.name] = tool

    def unregister_prefix(self, prefix: str) -> None:
        for name in [name for name in self._tools if name.startswith(prefix)]:
            del self._tools[name]

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def all(self) -> list[Tool]:
        return sorted(self._tools.values(), key=lambda tool: tool.name)

    def select(self, patterns: list[str]) -> list[Tool]:
        """Resolve a head's tool list; supports globs such as 'mcp__*'."""
        chosen: dict[str, Tool] = {}
        for pattern in patterns:
            for name, tool in self._tools.items():
                if fnmatch.fnmatchcase(name, pattern):
                    chosen[name] = tool
        return sorted(chosen.values(), key=lambda tool: tool.name)

    async def call(
        self,
        name: str,
        args: dict[str, Any],
        ctx: ToolContext,
        gate: ApprovalGate,
        timeout: float,
        output_limit: int,
        allowed: set[str] | None = None,
    ) -> ToolResult:
        started = time.perf_counter()
        tool = self._tools.get(name)
        if tool is None or (allowed is not None and name not in allowed):
            available = ", ".join(sorted(allowed or self._tools)) or "none"
            return ToolResult(False, f"Unknown tool '{name}'. Available: {available}")
        try:
            cleaned = validate_args(tool.parameters, args)
        except ToolError as exc:
            return ToolResult(False, f"Invalid arguments for {name}: {exc}")

        approved, reason = await gate.check(
            ApprovalRequest(name, tool.permission, cleaned, ctx.run_id, ctx.agent, ctx.origin)
        )
        if not approved:
            return ToolResult(False, f"Not executed: {reason}")

        try:
            if tool.blocking and not inspect.iscoroutinefunction(tool.handler):
                outcome = asyncio.to_thread(tool.handler, cleaned, ctx)
            else:
                outcome = tool.handler(cleaned, ctx)
            if inspect.isawaitable(outcome):
                outcome = await asyncio.wait_for(outcome, tool.timeout or timeout)
            content = outcome if isinstance(outcome, str) else json.dumps(outcome, default=str)
            ok = True
        except asyncio.TimeoutError:
            content, ok = f"{name} timed out after {tool.timeout or timeout:.0f}s", False
        except ToolError as exc:
            content, ok = str(exc), False
        except Exception as exc:  # report, never crash the head
            content, ok = f"{name} failed: {type(exc).__name__}: {exc}", False
        return ToolResult(ok, truncate(content, output_limit), time.perf_counter() - started)
