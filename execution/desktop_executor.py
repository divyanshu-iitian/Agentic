"""Narrow desktop executor for the actions exposed to the model."""

import subprocess
import time
from typing import Any

import keyboard as kb
import pyautogui

from core.config import get_config
from utils.logger import log

KNOWN_APPS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "chrome": "chrome.exe",
    "firefox": "firefox.exe",
    "brave": "brave.exe",
    "explorer": "explorer.exe",
    "outlook": "outlook.exe",
    "word": "winword.exe",
    "excel": "excel.exe",
}


class DesktopExecutor:
    """Execute a small, validated set of desktop actions."""

    def __init__(self):
        config = get_config()
        self.click_delay = config.execution.desktop.click_delay
        self.type_delay = config.execution.desktop.type_delay
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.1
        log.info("Desktop executor initialized")

    def execute(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        handlers = {
            "open_app": lambda: self._open_app(args),
            "click": lambda: self._click(args),
            "type": lambda: self._type(args),
            "scroll": lambda: self._scroll(args),
            "wait": lambda: self._wait(args),
            "vscode_open": self._vscode_open,
            "vscode_new_file": self._vscode_new_file,
            "vscode_save_file": lambda: self._vscode_save_file(args),
        }
        handler = handlers.get(action)
        if handler is None:
            return {"success": False, "error": f"Unknown desktop action: {action}"}

        try:
            log.info(f"Executing desktop action: {action}")
            return handler()
        except (OSError, KeyError, ValueError, pyautogui.FailSafeException) as exc:
            log.error(f"Desktop action failed: {exc}")
            return {"success": False, "error": str(exc)}

    def _open_app(self, args: dict[str, Any]) -> dict[str, Any]:
        app_name = str(args["name"]).strip().casefold()
        executable = KNOWN_APPS.get(app_name)
        if executable:
            subprocess.Popen([executable], shell=False)
            time.sleep(2)
            return {"success": True, "app": app_name}

        # Unknown but validated names use Windows search instead of a shell.
        kb.press_and_release("win")
        time.sleep(0.7)
        kb.write(app_name, delay=0.03)
        time.sleep(0.7)
        kb.press_and_release("enter")
        time.sleep(2)
        return {"success": True, "app": app_name, "method": "windows_search"}

    def _click(self, args: dict[str, Any]) -> dict[str, Any]:
        x, y = int(args["x"]), int(args["y"])
        width, height = pyautogui.size()
        if not (0 <= x < width and 0 <= y < height):
            return {"success": False, "error": f"Coordinates out of bounds: ({x}, {y})"}
        time.sleep(self.click_delay)
        pyautogui.click(x, y)
        return {"success": True, "x": x, "y": y}

    def _type(self, args: dict[str, Any]) -> dict[str, Any]:
        text = str(args["text"])
        time.sleep(self.type_delay)
        pyautogui.write(text, interval=0.03)
        return {"success": True, "text_length": len(text)}

    @staticmethod
    def _scroll(args: dict[str, Any]) -> dict[str, Any]:
        amount = int(args["amount"])
        pyautogui.scroll(amount)
        return {"success": True, "amount": amount}

    @staticmethod
    def _wait(args: dict[str, Any]) -> dict[str, Any]:
        seconds = float(args["seconds"])
        time.sleep(seconds)
        return {"success": True, "seconds": seconds}

    @staticmethod
    def _vscode_open() -> dict[str, Any]:
        kb.press_and_release("win")
        time.sleep(0.7)
        kb.write("Visual Studio Code", delay=0.03)
        time.sleep(0.7)
        kb.press_and_release("enter")
        time.sleep(2)
        return {"success": True, "app": "vscode"}

    @staticmethod
    def _vscode_new_file() -> dict[str, Any]:
        kb.press_and_release("ctrl+n")
        time.sleep(0.3)
        return {"success": True, "action": "new_file"}

    @staticmethod
    def _vscode_save_file(args: dict[str, Any]) -> dict[str, Any]:
        kb.press_and_release("ctrl+s")
        time.sleep(0.4)
        filename = str(args.get("filename", "")).strip()
        if filename:
            kb.write(filename, delay=0.03)
            kb.press_and_release("enter")
        return {"success": True, "action": "save_file"}

    @staticmethod
    def get_screen_size() -> tuple[int, int]:
        return pyautogui.size()

    @staticmethod
    def get_mouse_position() -> tuple[int, int]:
        return pyautogui.position()
