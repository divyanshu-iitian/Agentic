from agentic.tools.base import Tool, ToolContext, ToolError, ToolOutput, ToolRegistry, ToolResult
from agentic.tools.browser import browser_tools
from agentic.tools.core import core_tools
from agentic.tools.desktop import desktop_tools
from agentic.tools.files import file_tools
from agentic.tools.system import system_tools
from agentic.tools.web import web_tools


def builtin_tools() -> list[Tool]:
    return [
        *file_tools(),
        *system_tools(),
        *web_tools(),
        *browser_tools(),
        *core_tools(),
        *desktop_tools(),
    ]


__all__ = [
    "Tool",
    "ToolContext",
    "ToolError",
    "ToolOutput",
    "ToolRegistry",
    "ToolResult",
    "builtin_tools",
]
