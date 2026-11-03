"""Model Context Protocol client over stdio.

Each configured server is spawned as a subprocess. Its tools are listed at
startup and registered as `mcp__<server>__<tool>`, so any head whose tool
list matches (for example `mcp__*`) can call them. Every MCP tool runs under
the permission tier configured for its server.
"""

from __future__ import annotations

import json
import logging
import os
import queue
import re
import subprocess
import threading
from typing import Any

from agentic import __version__
from agentic.config import MCPServerConfig
from agentic.llm.base import ImagePart
from agentic.tools.base import Tool, ToolContext, ToolError, ToolOutput

PROTOCOL_VERSION = "2025-06-18"
SAFE_NAME = re.compile(r"[^a-zA-Z0-9_-]")
log = logging.getLogger("agentic.mcp")


class MCPClient:
    def __init__(self, name: str, config: MCPServerConfig, timeout: float = 60):
        self.name = name
        self.config = config
        self.timeout = timeout
        self.process: subprocess.Popen | None = None
        self._responses: queue.Queue = queue.Queue()
        self._lock = threading.Lock()
        self._next_id = 0
        self.server_info: dict[str, Any] = {}

    def start(self) -> None:
        env = {**os.environ, **{k: os.path.expandvars(v) for k, v in self.config.env.items()}}
        self.process = subprocess.Popen(
            [self.config.command, *self.config.args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=env,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        threading.Thread(target=self._read_loop, daemon=True, name=f"mcp-{self.name}").start()
        result = self.request(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "agentic", "version": __version__},
            },
        )
        self.server_info = result.get("serverInfo", {})
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _read_loop(self) -> None:
        assert self.process and self.process.stdout
        for line in self.process.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue  # servers sometimes log to stdout; ignore non-JSON lines
            if "id" in message and ("result" in message or "error" in message):
                self._responses.put(message)
        self._responses.put(None)

    def _send(self, message: dict[str, Any]) -> None:
        if not self.process or not self.process.stdin or self.process.poll() is not None:
            raise ToolError(f"MCP server '{self.name}' is not running")
        self.process.stdin.write(json.dumps(message) + "\n")
        self.process.stdin.flush()

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        with self._lock:
            self._next_id += 1
            request_id = self._next_id
            self._send(
                {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}
            )
            while True:
                try:
                    message = self._responses.get(timeout=self.timeout)
                except queue.Empty as exc:
                    raise ToolError(f"MCP server '{self.name}' did not answer {method}") from exc
                if message is None:
                    raise ToolError(f"MCP server '{self.name}' exited")
                if message.get("id") != request_id:
                    continue  # a late reply to a request that already timed out
                if "error" in message:
                    error = message["error"]
                    raise ToolError(f"MCP error {error.get('code')}: {error.get('message')}")
                return message.get("result") or {}

    def list_tools(self) -> list[dict[str, Any]]:
        tools: list[dict[str, Any]] = []
        cursor = None
        while True:
            result = self.request("tools/list", {"cursor": cursor} if cursor else {})
            tools.extend(result.get("tools", []))
            cursor = result.get("nextCursor")
            if not cursor:
                return tools

    def call_tool(self, name: str, arguments: dict[str, Any]) -> str | ToolOutput:
        result = self.request("tools/call", {"name": name, "arguments": arguments})
        parts: list[str] = []
        images: list[ImagePart] = []
        for block in result.get("content", []):
            if block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif block.get("type") == "image" and block.get("data"):
                images.append(ImagePart(block["data"], block.get("mimeType") or "image/png"))
                parts.append("[image attached]")
            elif block.get("type") == "resource":
                parts.append(json.dumps(block.get("resource", {}))[:4000])
            else:
                parts.append(f"[{block.get('type', 'unknown')} content omitted]")
        if not parts and "structuredContent" in result:
            parts.append(json.dumps(result["structuredContent"]))
        text = "\n".join(parts) or "(no content)"
        if result.get("isError"):
            raise ToolError(text)
        return ToolOutput(text, images) if images else text

    def close(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()


def mcp_tools(client: MCPClient) -> list[Tool]:
    tools = []
    server = SAFE_NAME.sub("_", client.name)
    for spec in client.list_tools():
        remote_name = spec["name"]
        parameters = spec.get("inputSchema") or {"type": "object", "properties": {}}
        # Keep the server's schema but let the server validate details.
        parameters = {
            "type": "object",
            "properties": parameters.get("properties", {}),
            "required": parameters.get("required", []),
        }

        def handler(
            args: dict[str, Any], ctx: ToolContext, _remote=remote_name
        ) -> str | ToolOutput:
            return client.call_tool(_remote, args)

        tools.append(
            Tool(
                f"mcp__{server}__{SAFE_NAME.sub('_', remote_name)}"[:64],
                (spec.get("description") or f"{remote_name} from MCP server {client.name}")[:1000],
                parameters,
                client.config.permission,
                handler,
                timeout=client.timeout + 5,
            )
        )
    return tools
