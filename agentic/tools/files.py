"""Workspace file tools. Every path is confined to the configured workspace."""

from __future__ import annotations

import fnmatch
import os
import re
from pathlib import Path
from typing import Any

from agentic.tools.base import Tool, ToolContext, ToolError, schema

MAX_READ_BYTES = 2_000_000
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".agentic"}


def resolve_in_workspace(ctx: ToolContext, raw: str) -> Path:
    workspace = ctx.workspace
    workspace.mkdir(parents=True, exist_ok=True)
    candidate = Path(raw.strip() or ".").expanduser()
    if not candidate.is_absolute():
        candidate = workspace / candidate
    resolved = candidate.resolve()
    if resolved != workspace and workspace not in resolved.parents:
        raise ToolError(f"Path '{raw}' is outside the workspace ({workspace})")
    return resolved


def _relative(ctx: ToolContext, path: Path) -> str:
    return path.relative_to(ctx.workspace).as_posix() or "."


def list_dir(args: dict[str, Any], ctx: ToolContext) -> str:
    path = resolve_in_workspace(ctx, args.get("path", "."))
    if not path.is_dir():
        raise ToolError(f"Not a directory: {args.get('path', '.')}")
    entries = []
    for child in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.casefold()))[:300]:
        if child.is_dir():
            entries.append(f"{child.name}/")
        else:
            entries.append(f"{child.name}  ({child.stat().st_size} bytes)")
    return "\n".join(entries) or "(empty directory)"


def read_file(args: dict[str, Any], ctx: ToolContext) -> str:
    path = resolve_in_workspace(ctx, args["path"])
    if not path.is_file():
        raise ToolError(f"File not found: {args['path']}")
    if path.stat().st_size > MAX_READ_BYTES:
        raise ToolError("File is larger than 2 MB; read a smaller file or search it")
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    start = max(1, int(args.get("start_line", 1)))
    count = int(args.get("max_lines", 400))
    window = lines[start - 1 : start - 1 + count]
    numbered = "\n".join(f"{start + i:>5}  {line}" for i, line in enumerate(window))
    footer = ""
    if start - 1 + count < len(lines):
        footer = f"\n... ({len(lines)} lines total; continue with start_line={start + count})"
    return (numbered or "(empty file)") + footer


def write_file(args: dict[str, Any], ctx: ToolContext) -> str:
    path = resolve_in_workspace(ctx, args["path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    content = args["content"]
    if args.get("append"):
        with path.open("a", encoding="utf-8") as handle:
            handle.write(content)
        return f"Appended {len(content)} characters to {_relative(ctx, path)}"
    path.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} characters to {_relative(ctx, path)}"


def edit_file(args: dict[str, Any], ctx: ToolContext) -> str:
    path = resolve_in_workspace(ctx, args["path"])
    if not path.is_file():
        raise ToolError(f"File not found: {args['path']}")
    text = path.read_text(encoding="utf-8")
    old, new = args["old_text"], args["new_text"]
    occurrences = text.count(old)
    if occurrences == 0:
        raise ToolError("old_text was not found; read the file and copy the exact text")
    if occurrences > 1 and not args.get("replace_all"):
        raise ToolError(f"old_text appears {occurrences} times; add context or set replace_all")
    count = occurrences if args.get("replace_all") else 1
    path.write_text(text.replace(old, new, count), encoding="utf-8")
    return f"Edited {_relative(ctx, path)} ({count} replacement{'s' if count > 1 else ''})"


def search_files(args: dict[str, Any], ctx: ToolContext) -> str:
    root = resolve_in_workspace(ctx, args.get("path", "."))
    glob = args.get("glob", "*")
    try:
        pattern = re.compile(args["pattern"], re.IGNORECASE)
    except re.error as exc:
        raise ToolError(f"Invalid regular expression: {exc}") from exc
    hits: list[str] = []
    for directory, subdirs, files in os.walk(root):
        subdirs[:] = [d for d in subdirs if d not in SKIP_DIRS]
        for filename in files:
            if not fnmatch.fnmatch(filename, glob):
                continue
            path = Path(directory) / filename
            try:
                if path.stat().st_size > MAX_READ_BYTES:
                    continue
                with path.open(encoding="utf-8", errors="ignore") as handle:
                    for number, line in enumerate(handle, 1):
                        if pattern.search(line):
                            hits.append(f"{_relative(ctx, path)}:{number}: {line.strip()[:200]}")
                            if len(hits) >= 200:
                                return "\n".join(hits) + "\n... (200 match limit)"
            except OSError:
                continue
    return "\n".join(hits) or "No matches."


def file_tools() -> list[Tool]:
    return [
        Tool(
            "list_dir",
            "List files and folders in a workspace directory.",
            schema({"path": {"type": "string", "description": "Directory, default '.'"}}),
            "read",
            list_dir,
        ),
        Tool(
            "read_file",
            "Read a text file from the workspace with line numbers.",
            schema(
                {
                    "path": {"type": "string"},
                    "start_line": {"type": "integer", "minimum": 1},
                    "max_lines": {"type": "integer", "minimum": 1, "maximum": 2000},
                },
                ["path"],
            ),
            "read",
            read_file,
        ),
        Tool(
            "write_file",
            "Create or overwrite a workspace file (set append=true to append).",
            schema(
                {
                    "path": {"type": "string"},
                    "content": {"type": "string", "maxLength": 1_000_000},
                    "append": {"type": "boolean"},
                },
                ["path", "content"],
            ),
            "write",
            write_file,
        ),
        Tool(
            "edit_file",
            "Replace exact text in a workspace file. old_text must match exactly.",
            schema(
                {
                    "path": {"type": "string"},
                    "old_text": {"type": "string"},
                    "new_text": {"type": "string"},
                    "replace_all": {"type": "boolean"},
                },
                ["path", "old_text", "new_text"],
            ),
            "write",
            edit_file,
        ),
        Tool(
            "search_files",
            "Search workspace files with a regular expression; returns path:line matches.",
            schema(
                {
                    "pattern": {"type": "string"},
                    "path": {"type": "string"},
                    "glob": {"type": "string", "description": "Filename filter such as *.py"},
                },
                ["pattern"],
            ),
            "read",
            search_files,
        ),
    ]
