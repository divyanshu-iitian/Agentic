"""Computer use: see the screen, operate any app, and draw.

Eyes
- desktop_ui_tree      the accessibility tree (Windows UI Automation): exact element
                       names, types, and positions, numbered for desktop_click_element
- desktop_screenshot   the screen as an image with a labeled coordinate grid
                       (offered only to models that can see images)
- desktop_read_screen  OCR text with coordinates, for models without vision
- desktop_windows      the open top-level windows

Hands
- desktop_open_app, desktop_window, desktop_click, desktop_click_element,
  desktop_type, desktop_hotkey, desktop_move, desktop_drag, desktop_draw,
  desktop_scroll, desktop_wait

Every tool that touches the screen carries the "desktop" permission (ask by
default). Moving the mouse into any screen corner triggers the failsafe, which
halts the whole run. Dependencies are imported lazily so the rest of the
runtime works on headless servers.
"""

from __future__ import annotations

import base64
import io
import math
import os
import re
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from typing import Any

from agentic.llm.base import ImagePart
from agentic.tools.base import Tool, ToolContext, ToolError, ToolOutput, schema

SAFE_APP = re.compile(r"^[\w .+\-]{1,80}$", re.UNICODE)
SAFE_KEYS = re.compile(r"^[a-z0-9]+(\+[a-z0-9]+){0,4}$")
MAX_SHAPES = 60
MAX_POINTS = 4_000
DRAW_UNITS = 1000  # shape coordinates inside a region run from 0 to 1000
INTERACTIVE_TYPES = {
    "Button", "SplitButton", "Edit", "Document", "CheckBox", "RadioButton", "ComboBox",
    "ListItem", "MenuItem", "MenuBar", "TabItem", "Hyperlink", "Slider", "Spinner",
    "TreeItem", "DataItem", "ToolBar", "Tab", "List", "Menu", "ScrollBar",
}  # fmt: skip
SW_RESTORE, SW_MAXIMIZE, SW_MINIMIZE = 9, 3, 6
Rect = tuple[int, int, int, int]  # left, top, right, bottom


# Shared helpers --------------------------------------------------------------


def _pyautogui():
    try:
        import pyautogui
    except ImportError as exc:
        raise ToolError("Desktop control needs pyautogui: pip install pyautogui") from exc
    except Exception as exc:  # no display, missing X server, and similar
        raise ToolError(f"Desktop control is unavailable here: {exc}") from exc
    pyautogui.FAILSAFE = True  # slam the mouse into a corner to abort
    return pyautogui


def _act(ctx: ToolContext, action: Callable[[Any], Any]) -> Any:
    """Run a GUI action; the corner failsafe halts the entire run."""
    gui = _pyautogui()
    if ctx.runtime.halt_reason:
        raise ToolError(f"Stopped: {ctx.runtime.halt_reason}")
    try:
        return action(gui)
    except gui.FailSafeException as exc:
        ctx.runtime.halt("the mouse was moved to a screen corner (failsafe)")
        raise ToolError("Emergency stop: mouse moved to a screen corner. Stopping.") from exc


def _uia():
    if sys.platform != "win32":
        raise ToolError(
            "The accessibility tree is available on Windows. On this system use "
            "desktop_screenshot (vision models) or desktop_read_screen instead."
        )
    try:
        import uiautomation
    except ImportError as exc:
        raise ToolError("Install UI Automation support: pip install uiautomation") from exc
    return uiautomation


def _element_rect(ctx: ToolContext, element_id: int) -> Rect:
    rect = ctx.runtime.desktop_elements.get(element_id)
    if rect is None:
        raise ToolError(f"Unknown element [{element_id}]. Call desktop_ui_tree first.")
    return rect


def _center(rect: Rect) -> tuple[int, int]:
    return (rect[0] + rect[2]) // 2, (rect[1] + rect[3]) // 2


# Apps and windows --------------------------------------------------------------


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
    time.sleep(float(args.get("wait_seconds", 2)))
    return (
        f"Opened {name}. Next: desktop_window to focus or maximize it, then "
        "desktop_ui_tree to see its controls."
    )


SHELL_WINDOWS = {"Program Manager", "Taskbar", "Start"}


def _is_minimized(control) -> bool:
    import ctypes

    hwnd = control.NativeWindowHandle
    return bool(hwnd) and bool(ctypes.windll.user32.IsIconic(hwnd))


def _top_windows(auto) -> list:
    """Named application windows, including minimized ones (they report 0x0)."""
    windows = []
    for control in auto.GetRootControl().GetChildren():
        if not control.Name or control.Name in SHELL_WINDOWS:
            continue
        rect = control.BoundingRectangle
        visible = rect.width() > 0 and rect.height() > 0 and not control.IsOffscreen
        if visible or _is_minimized(control):
            windows.append(control)
    return windows


def _find_window(auto, title: str | None):
    if not title:
        control = auto.GetForegroundControl()
        root = auto.GetRootControl()
        while control is not None:
            parent = control.GetParentControl()
            if parent is None or parent == root:
                return control
            control = parent
        raise ToolError("No foreground window")
    needle = title.casefold()
    matches = [w for w in _top_windows(auto) if needle in w.Name.casefold()]
    if not matches:
        raise ToolError(f"No window title contains '{title}'. Call desktop_windows to list them.")
    return matches[0]


def list_windows(args: dict[str, Any], ctx: ToolContext) -> str:
    auto = _uia()
    with auto.UIAutomationInitializerInThread():
        lines = []
        for window in _top_windows(auto):
            if _is_minimized(window):
                lines.append(f'"{window.Name}" (minimized)')
                continue
            r = window.BoundingRectangle
            lines.append(f'"{window.Name}" at ({r.left},{r.top}) size {r.width()}x{r.height()}')
    return "\n".join(lines) or "No visible windows."


def window(args: dict[str, Any], ctx: ToolContext) -> str:
    """Focus, maximize, minimize, or restore a window by part of its title."""
    import ctypes

    auto = _uia()
    action = args.get("action", "focus")
    with auto.UIAutomationInitializerInThread():
        target = _find_window(auto, args["title"])
        name = target.Name
        hwnd = target.NativeWindowHandle
    if not hwnd:
        raise ToolError(f"'{name}' has no native window handle")
    user32 = ctypes.windll.user32
    if action == "minimize":
        user32.ShowWindow(hwnd, SW_MINIMIZE)
        return f"minimize: '{name}'"
    user32.ShowWindow(hwnd, SW_MAXIMIZE if action == "maximize" else SW_RESTORE)
    _bring_to_front(hwnd)
    time.sleep(0.6)
    focused = user32.GetForegroundWindow() == hwnd
    return f"{action}: '{name}'" + ("" if focused else " (Windows kept another window in front)")


def _bring_to_front(hwnd: int) -> None:
    """Take the foreground without pressing keys (Alt would open ribbon key tips).

    Windows only lets the thread that owns the foreground window hand it over,
    so this thread briefly shares that thread's input state.
    """
    import ctypes

    user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
    foreground = user32.GetForegroundWindow()
    own_thread = kernel32.GetCurrentThreadId()
    foreground_thread = user32.GetWindowThreadProcessId(foreground, None)
    attached = foreground_thread and foreground_thread != own_thread
    if attached:
        user32.AttachThreadInput(foreground_thread, own_thread, True)
    try:
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        user32.SetFocus(hwnd)
    finally:
        if attached:
            user32.AttachThreadInput(foreground_thread, own_thread, False)


# Eyes ------------------------------------------------------------------------


def ui_tree(args: dict[str, Any], ctx: ToolContext) -> str:
    auto = _uia()
    limit = int(args.get("max_elements", 150))
    depth = int(args.get("max_depth", 25))
    deadline = time.monotonic() + 12
    elements: dict[int, Rect] = {}
    lines: list[str] = []
    seen: set[tuple[str, str, Rect]] = set()
    with auto.UIAutomationInitializerInThread():
        target = _find_window(auto, args.get("window"))
        r = target.BoundingRectangle
        header = f'Window "{target.Name}" at ({r.left},{r.top}) size {r.width()}x{r.height()}'
        for control, level in auto.WalkControl(target, includeTop=False, maxDepth=depth):
            if len(elements) >= limit or time.monotonic() > deadline:
                lines.append("... (more elements; narrow with window or max_elements)")
                break
            rect = control.BoundingRectangle
            if rect.width() <= 0 or rect.height() <= 0 or control.IsOffscreen:
                continue
            kind = control.ControlTypeName.removesuffix("Control")
            name = " ".join((control.Name or "").split())[:80]
            if not name and kind not in INTERACTIVE_TYPES:
                continue
            box = (rect.left, rect.top, rect.right, rect.bottom)
            if (kind, name, box) in seen:
                continue
            seen.add((kind, name, box))
            element_id = len(elements) + 1
            elements[element_id] = box
            cx, cy = _center(box)
            label = f' "{name}"' if name else ""
            lines.append(
                f"[{element_id}] {'  ' * min(level - 1, 6)}{kind}{label} "
                f"at ({cx},{cy}) size {rect.width()}x{rect.height()}"
            )
    ctx.runtime.desktop_elements = elements
    return (
        header
        + "\nUse desktop_click_element with an [id], or the (x,y) centers with desktop_click.\n"
        + ("\n".join(lines) or "(no accessible elements found; try desktop_screenshot)")
    )


def grid_lines(origin: int, length: int, step: int) -> list[int]:
    """Screen coordinates of grid lines that fall inside [origin, origin + length)."""
    first = math.ceil(origin / step) * step
    return list(range(first, origin + length, step))


def annotate(image, origin: tuple[int, int], width: int, grid: bool):
    """Downscale a screenshot and draw a grid labeled in screen coordinates."""
    from PIL import Image, ImageDraw, ImageFont

    scale = min(1.0, width / image.width)
    if scale < 1.0:
        image = image.resize(
            (round(image.width * scale), round(image.height * scale)), Image.LANCZOS
        )
    image = image.convert("RGB")
    if not grid:
        return image, scale
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    try:
        font = ImageFont.load_default(size=13)
    except TypeError:  # Pillow < 10.1
        font = ImageFont.load_default()
    screen_w, screen_h = image.width / scale, image.height / scale
    step = 100 if max(screen_w, screen_h) >= 800 else 50
    for x in grid_lines(origin[0], int(screen_w), step):
        px = (x - origin[0]) * scale
        draw.line([(px, 0), (px, image.height)], fill=(255, 0, 80, 70), width=1)
        draw.text((px + 2, 1), str(x), fill=(255, 0, 80, 230), font=font)
    for y in grid_lines(origin[1], int(screen_h), step):
        py = (y - origin[1]) * scale
        draw.line([(0, py), (image.width, py)], fill=(255, 0, 80, 70), width=1)
        draw.text((2, py + 1), str(y), fill=(255, 0, 80, 230), font=font)
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB"), scale


def screenshot(args: dict[str, Any], ctx: ToolContext) -> ToolOutput:
    settings = ctx.runtime.settings.computer
    region = None
    if args.get("element") is not None:
        left, top, right, bottom = _element_rect(ctx, int(args["element"]))
        region = (left, top, right - left, bottom - top)
    image = _act(ctx, lambda gui: gui.screenshot(region=region))
    origin = (region[0], region[1]) if region else (0, 0)
    annotated, scale = annotate(image, origin, settings.screenshot_width, settings.screenshot_grid)
    buffer = io.BytesIO()
    annotated.save(buffer, format="PNG", optimize=True)
    data = base64.b64encode(buffer.getvalue()).decode("ascii")
    grid_note = (
        " Grid labels are screen coordinates; use them directly."
        if settings.screenshot_grid
        else ""
    )
    return ToolOutput(
        f"Screenshot of {image.width}x{image.height} screen pixels at ({origin[0]},{origin[1]}), "
        f"shown at {scale:.2f}x.{grid_note}",
        [ImagePart(data)],
    )


def read_screen(args: dict[str, Any], ctx: ToolContext) -> str:
    """OCR the screen and return words with click coordinates."""
    image = _act(ctx, lambda gui: gui.screenshot())
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


# Hands -----------------------------------------------------------------------


def click(args: dict[str, Any], ctx: ToolContext) -> str:
    x, y = args["x"], args["y"]

    def do(gui):
        width, height = gui.size()
        if not (0 <= x < width and 0 <= y < height):
            raise ToolError(f"({x}, {y}) is outside the {width}x{height} screen")
        gui.click(x, y, clicks=2 if args.get("double") else 1, button=args.get("button", "left"))

    _act(ctx, do)
    return f"Clicked ({x}, {y})"


def click_element(args: dict[str, Any], ctx: ToolContext) -> str:
    x, y = _center(_element_rect(ctx, int(args["id"])))
    clicks = 2 if args.get("double") else 1
    _act(ctx, lambda gui: gui.click(x, y, clicks=clicks, button=args.get("button", "left")))
    time.sleep(0.3)
    return f"Clicked element [{args['id']}] at ({x}, {y})"


def type_text(args: dict[str, Any], ctx: ToolContext) -> str:
    text = args["text"]
    if args.get("element") is not None:
        x, y = _center(_element_rect(ctx, int(args["element"])))
        _act(ctx, lambda gui: gui.click(x, y))
        time.sleep(0.2)

    def do(gui):
        if text.isascii():
            gui.write(text, interval=0.015)
        elif sys.platform == "win32":
            # pyautogui cannot type non-ASCII; paste through the clipboard instead.
            _uia().SetClipboardText(text)
            gui.hotkey("ctrl", "v")
        else:
            raise ToolError("Typing non-ASCII text is supported on Windows only")
        if args.get("press_enter"):
            gui.press("enter")

    _act(ctx, do)
    return f"Typed {len(text)} characters"


def hotkey(args: dict[str, Any], ctx: ToolContext) -> str:
    keys = args["keys"].casefold().replace(" ", "")
    if not SAFE_KEYS.fullmatch(keys):
        raise ToolError("Use keys like 'ctrl+s', 'alt+tab', 'win+up', or 'enter'")
    _act(ctx, lambda gui: gui.hotkey(*keys.split("+")))
    time.sleep(0.2)
    return f"Pressed {keys}"


def move(args: dict[str, Any], ctx: ToolContext) -> str:
    _act(ctx, lambda gui: gui.moveTo(args["x"], args["y"], duration=0.2))
    return f"Moved the mouse to ({args['x']}, {args['y']})"


def scroll(args: dict[str, Any], ctx: ToolContext) -> str:
    amount = int(args["amount"])

    def do(gui):
        if "x" in args and "y" in args:
            gui.moveTo(args["x"], args["y"])
        gui.scroll(amount)

    _act(ctx, do)
    return f"Scrolled {'up' if amount > 0 else 'down'} {abs(amount)}"


def wait(args: dict[str, Any], ctx: ToolContext) -> str:
    time.sleep(float(args["seconds"]))
    return f"Waited {args['seconds']} seconds"


def densify(path: list[tuple[int, int]], max_step: float = 6.0) -> list[tuple[int, int]]:
    """Insert points so consecutive points are at most max_step pixels apart."""
    if len(path) < 2:
        return list(path)
    dense = [path[0]]
    for (x1, y1), (x2, y2) in zip(path, path[1:]):
        steps = max(1, math.ceil(math.hypot(x2 - x1, y2 - y1) / max_step))
        for i in range(1, steps + 1):
            dense.append((round(x1 + (x2 - x1) * i / steps), round(y1 + (y2 - y1) * i / steps)))
    return dense


def _points(raw: Any, label: str) -> list[tuple[float, float]]:
    if not isinstance(raw, list) or len(raw) < 2:
        raise ToolError(f"{label} needs a 'points' list of at least two [x, y] pairs")
    points = []
    for point in raw:
        if not (isinstance(point, list | tuple) and len(point) == 2):
            raise ToolError(f"{label}: each point must be [x, y]")
        points.append((float(point[0]), float(point[1])))
    return points


def shape_paths(
    shapes: list[dict[str, Any]], region: Rect | None = None
) -> list[list[tuple[int, int]]]:
    """Turn shape descriptions into screen-pixel polylines.

    With a region, coordinates run 0-1000 across its width and height and radii
    use the smaller axis so circles stay round. Without one, coordinates are
    absolute screen pixels.
    """
    if not isinstance(shapes, list) or not shapes:
        raise ToolError("shapes must be a non-empty list")
    if len(shapes) > MAX_SHAPES:
        raise ToolError(f"At most {MAX_SHAPES} shapes per call")
    if region:
        left, top, right, bottom = region
        sx, sy = (right - left) / DRAW_UNITS, (bottom - top) / DRAW_UNITS
    else:
        left = top = 0
        right = bottom = 100_000
        sx = sy = 1.0
    sr = min(sx, sy)

    def to_screen(x: float, y: float) -> tuple[int, int]:
        px = min(max(left + x * sx, left + 2), right - 3)
        py = min(max(top + y * sy, top + 2), bottom - 3)
        return round(px), round(py)

    def ellipse(cx: float, cy: float, rx: float, ry: float) -> list[tuple[int, int]]:
        segments = max(24, min(120, int((rx + ry) / 4)))
        return [
            to_screen(cx + rx * math.cos(2 * math.pi * i / segments) / sx,
                      cy + ry * math.sin(2 * math.pi * i / segments) / sy)
            for i in range(segments + 1)
        ]  # fmt: skip

    paths: list[list[tuple[int, int]]] = []
    for index, shape in enumerate(shapes, 1):
        if not isinstance(shape, dict):
            raise ToolError(f"shape {index} must be an object")
        kind = str(shape.get("type", "")).casefold()
        label = f"shape {index} ({kind or 'no type'})"
        try:
            if kind in {"line", "polyline", "path", "freehand"}:
                paths.append([to_screen(x, y) for x, y in _points(shape.get("points"), label)])
            elif kind in {"polygon", "triangle"}:
                points = [to_screen(x, y) for x, y in _points(shape.get("points"), label)]
                paths.append([*points, points[0]])
            elif kind in {"rect", "rectangle", "square"}:
                x, y = float(shape["x"]), float(shape["y"])
                w = float(shape.get("w", shape.get("width", shape.get("size", 0))))
                h = float(shape.get("h", shape.get("height", w if kind == "square" else 0)))
                corners = [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]
                paths.append([to_screen(px, py) for px, py in corners])
            elif kind == "circle":
                r = float(shape["r"] if "r" in shape else shape["radius"]) * sr
                paths.append(ellipse(float(shape["cx"]), float(shape["cy"]), r, r))
            elif kind in {"ellipse", "oval"}:
                rx, ry = float(shape["rx"]) * sx, float(shape["ry"]) * sy
                paths.append(ellipse(float(shape["cx"]), float(shape["cy"]), rx, ry))
            else:
                raise ToolError(
                    f"{label}: type must be line, polyline, polygon, rect, circle, or ellipse"
                )
        except (KeyError, TypeError, ValueError) as exc:
            raise ToolError(f"{label} is missing or has an invalid field: {exc}") from exc
    if sum(len(path) for path in paths) > MAX_POINTS:
        raise ToolError(f"Too many points (max {MAX_POINTS})")
    return paths


MOUSE_FLAGS = {  # MOUSEEVENTF_* down/up pairs per button
    "left": (0x0002, 0x0004),
    "right": (0x0008, 0x0010),
    "middle": (0x0020, 0x0040),
}
MOUSEEVENTF_MOVE_ABSOLUTE = 0x0001 | 0x8000 | 0x4000  # MOVE | ABSOLUTE | VIRTUALDESK


class _WindowsMouse:
    """Real input events through mouse_event.

    pyautogui moves the cursor with SetCursorPos, which modern apps such as the
    new Paint ignore while a button is held, so strokes would vanish.
    """

    def __init__(self) -> None:
        import ctypes

        self.user32 = ctypes.windll.user32
        # Virtual desktop origin and size, so multi-monitor setups map correctly.
        self.left = self.user32.GetSystemMetrics(76)
        self.top = self.user32.GetSystemMetrics(77)
        self.width = max(1, self.user32.GetSystemMetrics(78) - 1)
        self.height = max(1, self.user32.GetSystemMetrics(79) - 1)

    def move(self, x: int, y: int) -> None:
        nx = round((x - self.left) * 65535 / self.width)
        ny = round((y - self.top) * 65535 / self.height)
        self.user32.mouse_event(MOUSEEVENTF_MOVE_ABSOLUTE, nx, ny, 0, 0)

    def press(self, button: str, down: bool) -> None:
        self.user32.mouse_event(MOUSE_FLAGS[button][0 if down else 1], 0, 0, 0, 0)


def _stroke(
    gui,
    paths: list[list[tuple[int, int]]],
    button: str,
    stopped: Callable[[], str | None] = lambda: None,
) -> int:
    mouse = _WindowsMouse() if sys.platform == "win32" else None
    corners = _failsafe_corners(gui)
    strokes = 0
    for path in paths:
        dense = densify(path)
        if mouse:
            mouse.move(*dense[0])
            time.sleep(0.03)
            mouse.press(button, True)
        else:
            gui.moveTo(*dense[0], _pause=False)
            gui.mouseDown(button=button, _pause=False)
        time.sleep(0.03)  # let the app register the press before movement
        try:
            for x, y in dense[1:]:
                if tuple(gui.position()) in corners:
                    raise gui.FailSafeException("mouse moved to a corner")
                if stopped():  # Ctrl+Alt+Q or another emergency stop mid-stroke
                    raise ToolError(f"Stopped: {stopped()}")
                if mouse:
                    mouse.move(x, y)
                else:
                    gui.moveTo(x, y, _pause=False)
                time.sleep(0.004)
        finally:
            time.sleep(0.02)
            if mouse:
                mouse.press(button, False)
            else:
                gui.mouseUp(button=button, _pause=False)
        strokes += 1
        time.sleep(0.08)
    return strokes


def _failsafe_corners(gui) -> set[tuple[int, int]]:
    """The screen corners that trigger the emergency stop."""
    width, height = gui.size()
    return {(0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)}


def drag(args: dict[str, Any], ctx: ToolContext) -> str:
    points = [(round(x), round(y)) for x, y in _points(args["points"], "drag")]
    if len(points) > 500:
        raise ToolError("At most 500 points per drag")
    button = args.get("button", "left")
    _act(ctx, lambda gui: _stroke(gui, [points], button, lambda: ctx.runtime.halt_reason))
    return f"Dragged through {len(points)} points from {points[0]} to {points[-1]}"


def draw(args: dict[str, Any], ctx: ToolContext) -> str:
    region: Rect | None = None
    if args.get("element") is not None:
        region = _element_rect(ctx, int(args["element"]))
    elif args.get("region"):
        r = args["region"]
        try:
            region = (int(r["x"]), int(r["y"]), int(r["x"]) + int(r["width"]),
                      int(r["y"]) + int(r["height"]))  # fmt: skip
        except (KeyError, TypeError, ValueError) as exc:
            raise ToolError("region needs x, y, width, height") from exc
    paths = shape_paths(args["shapes"], region)
    button = args.get("button", "left")
    strokes = _act(ctx, lambda gui: _stroke(gui, paths, button, lambda: ctx.runtime.halt_reason))
    where = f"inside region {region}" if region else "in screen coordinates"
    return f"Drew {strokes} stroke(s) {where}. Verify with desktop_screenshot if you can see."


SHAPE_HELP = (
    "Draw shapes with the mouse in the current tool (for example Paint's brush). Shapes: "
    '{"type":"line","points":[[x,y],...]}, {"type":"polygon","points":[...]}, '
    '{"type":"rect","x":..,"y":..,"w":..,"h":..}, {"type":"circle","cx":..,"cy":..,"r":..}, '
    '{"type":"ellipse","cx":..,"cy":..,"rx":..,"ry":..}. With element (a canvas id from '
    "desktop_ui_tree) or region, coordinates run 0-1000 across that area; otherwise they "
    "are screen pixels. Send the whole picture in one call."
)


def desktop_tools() -> list[Tool]:
    xy = {"x": {"type": "integer", "minimum": 0}, "y": {"type": "integer", "minimum": 0}}
    button = {"type": "string", "enum": ["left", "right", "middle"]}
    return [
        Tool(
            "desktop_open_app",
            "Open a desktop application by name, such as mspaint, notepad, calc, or chrome.",
            schema(
                {
                    "name": {"type": "string", "maxLength": 80},
                    "wait_seconds": {"type": "number", "minimum": 0, "maximum": 15},
                },
                ["name"],
            ),
            "desktop",
            open_app,
        ),
        Tool(
            "desktop_windows",
            "List open windows with their titles, positions, and sizes.",
            schema({}),
            "desktop",
            list_windows,
        ),
        Tool(
            "desktop_window",
            "Bring a window to the front (focus), or maximize, minimize, or restore it. "
            "title is any part of the window title.",
            schema(
                {
                    "title": {"type": "string", "maxLength": 200},
                    "action": {
                        "type": "string",
                        "enum": ["focus", "maximize", "minimize", "restore"],
                    },
                },
                ["title"],
            ),
            "desktop",
            window,
        ),
        Tool(
            "desktop_ui_tree",
            "List the buttons, menus, fields, and other controls of a window (default: the "
            "foreground window) with numbered ids and screen positions. The most reliable "
            "way to find what to click.",
            schema(
                {
                    "window": {"type": "string", "description": "part of the window title"},
                    "max_elements": {"type": "integer", "minimum": 10, "maximum": 400},
                    "max_depth": {"type": "integer", "minimum": 1, "maximum": 50},
                }
            ),
            "desktop",
            ui_tree,
            timeout=30,
        ),
        Tool(
            "desktop_screenshot",
            "Look at the screen (or one element) as an image with a coordinate grid. "
            "Grid labels are screen coordinates you can click.",
            schema({"element": {"type": "integer", "minimum": 1}}),
            "desktop",
            screenshot,
            requires_vision=True,
        ),
        Tool(
            "desktop_read_screen",
            "OCR the screen; returns text lines with click coordinates.",
            schema({}),
            "desktop",
            read_screen,
        ),
        Tool(
            "desktop_click",
            "Click at screen coordinates.",
            schema({**xy, "button": button, "double": {"type": "boolean"}}, ["x", "y"]),
            "desktop",
            click,
        ),
        Tool(
            "desktop_click_element",
            "Click the center of an element by its [id] from the last desktop_ui_tree.",
            schema(
                {
                    "id": {"type": "integer", "minimum": 1},
                    "button": button,
                    "double": {"type": "boolean"},
                },
                ["id"],
            ),
            "desktop",
            click_element,
        ),
        Tool(
            "desktop_type",
            "Type text into the focused control, or into an element id (clicked first).",
            schema(
                {
                    "text": {"type": "string", "maxLength": 20_000},
                    "element": {"type": "integer", "minimum": 1},
                    "press_enter": {"type": "boolean"},
                },
                ["text"],
            ),
            "desktop",
            type_text,
        ),
        Tool(
            "desktop_hotkey",
            "Press a key or combination such as 'ctrl+s', 'alt+tab', 'win+up', or 'enter'.",
            schema({"keys": {"type": "string", "maxLength": 60}}, ["keys"]),
            "desktop",
            hotkey,
        ),
        Tool(
            "desktop_move",
            "Move the mouse to screen coordinates without clicking (for hover menus).",
            schema(xy, ["x", "y"]),
            "desktop",
            move,
        ),
        Tool(
            "desktop_drag",
            "Hold a mouse button and drag through a list of [x, y] screen points "
            "(drag and drop, sliders, selections, freehand strokes).",
            schema(
                {"points": {"type": "array", "items": {"type": "array"}}, "button": button},
                ["points"],
            ),
            "desktop",
            drag,
            timeout=120,
        ),
        Tool(
            "desktop_draw",
            SHAPE_HELP,
            schema(
                {
                    "shapes": {"type": "array", "items": {"type": "object"}},
                    "element": {"type": "integer", "minimum": 1},
                    "region": {"type": "object"},
                    "button": button,
                },
                ["shapes"],
            ),
            "desktop",
            draw,
            timeout=300,
        ),
        Tool(
            "desktop_scroll",
            "Scroll the mouse wheel: positive amount scrolls up, negative down. Optionally "
            "at x, y.",
            schema(
                {"amount": {"type": "integer", "minimum": -5000, "maximum": 5000}, **xy},
                ["amount"],
            ),
            "desktop",
            scroll,
        ),
        Tool(
            "desktop_wait",
            "Wait for an app or page to finish loading.",
            schema({"seconds": {"type": "number", "minimum": 0.1, "maximum": 30}}, ["seconds"]),
            "read",
            wait,
            timeout=35,
        ),
    ]
