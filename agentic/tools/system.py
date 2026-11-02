"""Shell and Python execution inside the workspace.

Both tools carry the "execute" permission, which asks the user by default.
The pattern guard below blocks a handful of catastrophic commands as defense
in depth; it is not a sandbox, and approval remains the real boundary.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from typing import Any

from agentic.tools.base import Tool, ToolContext, ToolError, schema
from agentic.tools.files import resolve_in_workspace

DANGEROUS_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\brm\s+(-[a-z]*\s+)*-[a-z]*r[a-z]*\s+(-[a-z]*\s+)*(/|~|\*|\$home)(\s|$)",
        r"\bmkfs(\.\w+)?\b",
        r"\bdd\s+.*\bof=/dev/",
        r":\(\)\s*\{\s*:\|:&\s*\};:",
        r"\bformat(\.com)?\s+[a-z]:",
        r"(^|[;&|]\s*)(sudo\s+)?(shutdown|reboot|poweroff|halt)(\.exe)?(\s|$)",
        r"\b(stop|restart)-computer\b",
        r"\bdiskpart\b",
        r"\bcipher\s+/w",
        r"\breg(\.exe)?\s+delete\s+hklm",
        r"\bdel\s+(/[a-z]\s+)*[a-z]:\\\s*(\*|$)",
        r"remove-item\s+.*-recurse.*\s[a-z]:\\\s*($|\s)",
        r"\bchmod\s+-r\s+777\s+/\s*$",
    )
]


SHELL_STYLE_PYTHON = re.compile(r"^\s*(python3?|py)(\.exe)?\s+[\w./\-]+\.py\b[^\n]*$")


def check_command(command: str) -> None:
    for pattern in DANGEROUS_PATTERNS:
        if pattern.search(command):
            raise ToolError("Blocked: this command matches a destructive-command guard.")


def _shell_argv(command: str) -> list[str]:
    if sys.platform == "win32":
        return ["powershell", "-NoProfile", "-NonInteractive", "-Command", command]
    return ["/bin/sh", "-c", command]


def _format(completed: subprocess.CompletedProcess) -> str:
    parts = [f"exit code: {completed.returncode}"]
    if completed.stdout:
        parts.append(f"stdout:\n{completed.stdout.rstrip()}")
    if completed.stderr:
        parts.append(f"stderr:\n{completed.stderr.rstrip()}")
    return "\n".join(parts)


def run_command(args: dict[str, Any], ctx: ToolContext) -> str:
    command = args["command"]
    check_command(command)
    cwd = resolve_in_workspace(ctx, args.get("cwd", "."))
    timeout = int(args.get("timeout", ctx.runtime.settings.limits.tool_timeout))
    try:
        completed = subprocess.run(
            _shell_argv(command),
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
    except subprocess.TimeoutExpired as exc:
        raise ToolError(f"Command timed out after {timeout}s") from exc
    except FileNotFoundError as exc:
        raise ToolError(f"Shell not found: {exc}") from exc
    return _format(completed)


def run_python(args: dict[str, Any], ctx: ToolContext) -> str:
    if SHELL_STYLE_PYTHON.match(args["code"]):
        raise ToolError(
            "run_python takes Python source code, not a shell command. "
            f"To run a file, call run_command with: {args['code'].strip()}"
        )
    timeout = int(args.get("timeout", ctx.runtime.settings.limits.tool_timeout))
    ctx.workspace.mkdir(parents=True, exist_ok=True)
    try:
        completed = subprocess.run(
            [sys.executable, "-I", "-"],
            input=args["code"],
            cwd=ctx.workspace,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
    except subprocess.TimeoutExpired as exc:
        raise ToolError(f"Python timed out after {timeout}s") from exc
    return _format(completed)


def system_tools() -> list[Tool]:
    shell_name = "PowerShell" if sys.platform == "win32" else "/bin/sh"
    return [
        Tool(
            "run_command",
            f"Run a {shell_name} command in the workspace and return exit code and output.",
            schema(
                {
                    "command": {"type": "string", "maxLength": 8_000},
                    "cwd": {"type": "string", "description": "Workspace-relative directory"},
                    "timeout": {"type": "integer", "minimum": 1, "maximum": 1800},
                },
                ["command"],
            ),
            "execute",
            run_command,
            timeout=1860,
        ),
        Tool(
            "run_python",
            "Execute Python source code (not a shell command) in the workspace and return stdout. "
            "Use print() for results. To run an existing .py file, use run_command instead.",
            schema(
                {
                    "code": {"type": "string", "maxLength": 100_000},
                    "timeout": {"type": "integer", "minimum": 1, "maximum": 1800},
                },
                ["code"],
            ),
            "execute",
            run_python,
            timeout=1860,
        ),
    ]
