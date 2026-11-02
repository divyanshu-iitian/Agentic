"""Desktop control: open apps, type, press keys, click, and read the screen.

These tools carry the "desktop" permission (ask by default). Dependencies
are imported lazily so the rest of the runtime works on headless servers.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import time
from typing import Any

from agentic.tools.base import Tool, ToolContext, ToolError, schema

SAFE_APP = re.compile(r"^[\w .+\-]{1,80}$", re.UNICODE)
SAFE_KEYS = re.compile(r"^[a-z0-9]+(\+[a-z0-9]+){0,4}$")


def _pyautogui():
    try:
        import pyautogui
    except ImportError as exc:
        raise ToolError("Desktop control needs pyautogui: pip install pyautogui") from exc
    except Exception as exc:  # no display, missing X server, and similar
        raise ToolError(f"Desktop control is unavailable here: {exc}") from exc
    pyautogui.FAILSAFE = True  # slam the mouse into a corner to abort
    return pyautogui


def open_app(args: dict[str, Any], ctx: ToolContext) -> str:
    name = args["name"].strip()
    if not SAFE_APP.fullmatch(name):
        raise ToolError("Application name contains unsupported characters")
    if sys.platform == "win32":
        try:
            os.startfile(name)  # type: ignore[attr-defined]  # ShellExecute, no shell parsing
        except OSError as exc:
            raise ToolError(f"Could not open '{name}': {exc.strerror or exc}") from exc
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-a", name])
    else:
        executable = shutil.which(name)
        if not executable:
            raise ToolError(f"'{name}' was not found on PATH")
        subprocess.Popen([executable], start_new_session=True)
    time.sleep(1.5)
    return f"Opened {name}"


def type_text(args: dict[str, Any], ctx: ToolContext) -> str:
    gui = _pyautogui()
    gui.write(args["text"], interval=0.02)
    if args.get("press_enter"):
        gui.press("enter")
    return f"Typed {len(args['text'])} characters"


def hotkey(args: dict[str, Any], ctx: ToolContext) -> str:
    keys = args["keys"].casefold().replace(" ", "")
    if not SAFE_KEYS.fullmatch(keys):
        raise ToolError("Use keys like 'ctrl+s', 'alt+tab', or 'enter'")
    _pyautogui().hotkey(*keys.split("+"))
    return f"Pressed {keys}"


def click(args: dict[str, Any], ctx: ToolContext) -> str:
    gui = _pyautogui()
    width, height = gui.size()
    x, y = args["x"], args["y"]
    if not (0 <= x < width and 0 <= y < height):
        raise ToolError(f"({x}, {y}) is outside the {width}x{height} screen")
    gui.click(x, y, clicks=2 if args.get("double") else 1, button=args.get("button", "left"))
    return f"Clicked ({x}, {y})"


def read_screen(args: dict[str, Any], ctx: ToolContext) -> str:
    """OCR the screen and return words with click coordinates."""
    gui = _pyautogui()
    image = gui.screenshot()
    try:
        import pytesseract
    except ImportError as exc:
        raise ToolError("Screen reading needs pytesseract and the Tesseract binary") from exc
    try:
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    except pytesseract.TesseractNotFoundError as exc:
        raise ToolError("Install Tesseract OCR and add it to PATH") from exc

    lines: dict[tuple[int, int, int], list[tuple[str, int, int]]] = {}
    for i, word in enumerate(data["text"]):
        word = word.strip()
        if not word or float(data["conf"][i]) < 40:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        cx = data["left"][i] + data["width"][i] // 2
        cy = data["top"][i] + data["height"][i] // 2
        lines.setdefault(key, []).append((word, cx, cy))
    rendered = [
        f"({words[0][1]},{words[0][2]}) " + " ".join(w for w, _, _ in words)
        for words in lines.values()
    ]
    width, height = image.size
    return f"Screen {width}x{height}. Lines start with the (x,y) of their first word:\n" + (
        "\n".join(rendered[:250]) or "(no readable text)"
    )


def desktop_tools() -> list[Tool]:
    return [
        Tool(
            "desktop_open_app",
            "Open a desktop application by name, such as notepad or calc.",
            schema({"name": {"type": "string", "maxLength": 80}}, ["name"]),
            "desktop",
            open_app,
        ),
        Tool(
            "desktop_type",
            "Type text into the focused window.",
            schema(
                {
                    "text": {"type": "string", "maxLength": 20_000},
                    "press_enter": {"type": "boolean"},
                },
                ["text"],
            ),
            "desktop",
            type_text,
        ),
        Tool(
            "desktop_hotkey",
            "Press a key or key combination such as 'ctrl+s', 'alt+tab', or 'enter'.",
            schema({"keys": {"type": "string", "maxLength": 60}}, ["keys"]),
            "desktop",
            hotkey,
        ),
        Tool(
            "desktop_click",
            "Click at screen coordinates. Read the screen first to find coordinates.",
            schema(
                {
                    "x": {"type": "integer", "minimum": 0},
                    "y": {"type": "integer", "minimum": 0},
                    "button": {"type": "string", "enum": ["left", "right", "middle"]},
                    "double": {"type": "boolean"},
                },
                ["x", "y"],
            ),
            "desktop",
            click,
        ),
        Tool(
            "desktop_read_screen",
            "Capture the screen and OCR it; returns text lines with click coordinates.",
            schema({}),
            "desktop",
            read_screen,
        ),
    ]
