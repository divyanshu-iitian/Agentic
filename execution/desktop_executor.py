"""
Desktop Executor

Executes desktop automation actions using pyautogui and keyboard.
"""

import time
import subprocess
import pyautogui
import keyboard as kb
from typing import Dict, Any, Optional
from core.config import get_config
from utils.logger import log
# 🧠 NEW: Vision Client
from perception.vision_client import VisionClient


from core.world_model import WorldModel

class DesktopExecutor:
    """Execute desktop automation actions"""
    
    def __init__(self, vision_client: Optional[VisionClient] = None, world_model: Optional[WorldModel] = None):
        config = get_config()
        self.click_delay = config.execution.desktop.click_delay
        self.type_delay = config.execution.desktop.type_delay
        self.vision_client = vision_client
        self.world_model = world_model
        
        # PyAutoGUI safety settings
        pyautogui.FAILSAFE = True  # Move mouse to corner to abort
        pyautogui.PAUSE = 0.1
        
        log.info("Desktop executor initialized")
    
    def execute(self, action: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a desktop action.
        
        Args:
            action: Action name
            args: Action arguments
            
        Returns:
            Execution result
        """
        log.info(f"Executing desktop action: {action}")
        
        try:
            if action == "open_app":
                return self._open_app(args)
            elif action == "click":
                return self._click(args)
            elif action == "click_element": # 👁️ NEW: Vision Click
                return self._click_element(args)
            elif action == "type":
                return self._type(args)
            elif action == "scroll":
                return self._scroll(args)
            elif action == "press_key":
                return self._press_key(args)
            elif action == "wait":
                return self._wait(args)
            elif action == "launch_app":
                return self._launch_app_via_search(args)
            # 🧠 SEMANTIC ACTIONS
            elif action == "browser_open" or action == "browser_search":
                return self._browser_nav(args)
            elif action == "vscode_open":
                return self._vscode_open()
            elif action == "vscode_new_file":
                return self._vscode_new_file()
            elif action == "vscode_save_file":
                return self._vscode_save_file(args)
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
        
        except Exception as e:
            log.error(f"Desktop action failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _open_app(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Open an application"""
        app_name = args["name"].lower()
        
        # Windows app launch mapping
        app_commands = {
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
        
        command = app_commands.get(app_name, app_name)
        
        try:
            subprocess.Popen(command, shell=True)
            time.sleep(5)  # Give app more time to open (increased from 2s to 5s)
            log.info(f"Opened application: {app_name}")
            return {"success": True, "app": app_name}
        except Exception as e:
            log.error(f"Failed to open {app_name}: {e}")
            return {"success": False, "error": str(e)}
    
    def _click(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Click at coordinates"""
        x = int(args["x"])
        y = int(args["y"])
        
        # Validate coordinates
        screen_width, screen_height = pyautogui.size()
        if not (0 <= x < screen_width and 0 <= y < screen_height):
            return {
                "success": False,
                "error": f"Coordinates out of bounds: ({x}, {y})"
            }
        
        time.sleep(self.click_delay)
        pyautogui.click(x, y)
        log.info(f"Clicked at ({x}, {y})")
        
        return {"success": True, "x": x, "y": y}
        
    def _click_element(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Click UI element using Vision (Llava)"""
        if not self.vision_client:
             return {"success": False, "error": "Vision capabilities not initialized"}
             
        element_name = args.get("name", "unknown")
        log.info(f"👁️ Vision Looking for: {element_name}")
        
        # 1. Capture strict screenshot for analysis
        temp_path = "temp_vision_context.png"
        try:
            pyautogui.screenshot(temp_path)
        except Exception as e:
            return {"success": False, "error": f"Screenshot failed: {e}"}
            
        # 2. Ask Vision Model
        coords = self.vision_client.detect_element(temp_path, element_name)
        
        if not coords:
            return {"success": False, "error": f"Element '{element_name}' not detected visualy"}
            
        x, y = coords
        log.info(f"👁️ Vision Found '{element_name}' at ({x}, {y})")
        
        # 3. Click
        time.sleep(self.click_delay)
        pyautogui.click(x, y)
        
        return {"success": True, "element": element_name, "x": x, "y": y}
    
    def _type(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Type text"""
        text = args["text"]
        
        time.sleep(self.type_delay)
        pyautogui.write(text, interval=0.05)
        log.info(f"Typed text: {text[:50]}...")
        
        return {"success": True, "text_length": len(text)}
    
    def _scroll(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Scroll by amount (positive=up, negative=down)"""
        amount = int(args["amount"])
        
        pyautogui.scroll(amount)
        log.info(f"Scrolled: {amount}")
        
        return {"success": True, "amount": amount}
    
    def _wait(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Wait for specified seconds"""
        seconds = float(args["seconds"])
        
        if seconds > 10:
            log.warning(f"Long wait requested: {seconds}s")
        
        time.sleep(seconds)
        log.info(f"Waited {seconds}s")
        
        return {"success": True, "seconds": seconds}

    def _press_key(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Press a specific key or combination"""
        key = args["key"]
        
        # 🧠 AGENT 2.0: Context Checking
        if key == "win" and self.world_model and self.world_model.state.is_start_menu_open:
            log.info("🧠 Skipping 'win' press: Start Menu is ALREADY open according to World Model")
            return {"success": True, "skipped": True, "reason": "Start Menu already open"}
        
        try:
            # Handle special keys safely
            kb.press_and_release(key)
            time.sleep(0.5)  # Small delay after key press
            log.info(f"Pressed key: {key}")
            return {"success": True, "key": key}
        except Exception as e:
            log.error(f"Failed to press key {key}: {e}")
            return {"success": False, "error": str(e)}
    
    # 🧠 SEMANTIC VS CODE ACTIONS (SMART!)
    
    def _vscode_open(self) -> Dict[str, Any]:
        """Open VS Code using keyboard shortcut or command"""
        try:
            # Try Windows search
            kb.press_and_release("win")
            time.sleep(0.5)
            kb.write("code", delay=0.05)
            time.sleep(0.3)
            kb.press_and_release("enter")
            time.sleep(2)  # Wait for VS Code to open
            
            log.info("✅ Opened VS Code (semantic)")
            return {"success": True, "app": "vscode"}
        except Exception as e:
            log.error(f"Failed to open VS Code: {e}")
            return {"success": False, "error": str(e)}
    
    def _vscode_new_file(self) -> Dict[str, Any]:
        """Create new file in VS Code (Ctrl+N)"""
        try:
            kb.press_and_release("ctrl+n")
            time.sleep(0.5)
            
            log.info("✅ Created new file in VS Code (semantic)")
            return {"success": True, "action": "new_file"}
        except Exception as e:
            log.error(f"Failed to create new file: {e}")
            return {"success": False, "error": str(e)}
    
    def _vscode_save_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Save current file in VS Code (Ctrl+S)"""
        try:
            kb.press_and_release("ctrl+s")
            time.sleep(0.5)
            
            # If filename provided, type it
            if "filename" in args and args["filename"]:
                time.sleep(0.5)
                kb.write(args["filename"], delay=0.05)
                time.sleep(0.3)
                kb.press_and_release("enter")
            
            log.info("✅ Saved file in VS Code (semantic)")
            return {"success": True, "action": "save_file"}
        except Exception as e:
            log.error(f"Failed to save file: {e}")
            return {"success": False, "error": str(e)}
    
    def get_screen_size(self) -> tuple[int, int]:
        """Get screen dimensions"""
        return pyautogui.size()
    
    def get_mouse_position(self) -> tuple[int, int]:
        """Get current mouse position"""
        return pyautogui.position()

    def _launch_app_via_search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Launch an app using the Start Menu Search (Atomic Sequence).
        
        Sequence: Win -> Wait -> Type -> Wait -> Enter
        This prevents the "Observe Loop" failure where the agent sees the desktop
        before the start menu opens and tries to press Win again (closing it).
        """
        app_name = args["name"]
        log.info(f"🚀 Launching app via search: {app_name}")
        
        try:
            # 1. Press Win
            kb.press_and_release("win")
            
            # 2. WAIT for animation (Critical!)
            # Windows Start Menu animation usually takes 0.5-1.0s
            time.sleep(1.5)
            
            # 3. Type App Name
            kb.write(app_name, delay=0.05)
            
            # 4. Wait for search results
            time.sleep(1.0)
            
            # 5. Press Enter to launch top result
            kb.press_and_release("enter")
            
            # 6. Wait for app to actually launch before giving control back
            time.sleep(6.0)
            
            return {"success": True, "app": app_name, "method": "search_atomic"}
            
        except Exception as e:
            log.error(f"Failed to launch app {app_name}: {e}")
            return {"success": False, "error": str(e)}

    def _browser_nav(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Robust Browser Navigation/Search.
        Uses Ctrl+L to focus address bar -> Type -> Enter.
        Works in Chrome, Firefox, Edge, Brave.
        """
        url_or_query = args.get("url") or args.get("query")
        log.info(f"🌐 Robust Browser Nav: {url_or_query}")
        
        try:
            # 1. Focus Address Bar
            # Try Ctrl+L first (Standard)
            kb.press_and_release("ctrl+l")
            time.sleep(0.5)
            
            # 2. Type URL/Query
            # We use a slightly faster typing speed for long URLs
            kb.write(url_or_query, delay=0.02)
            time.sleep(0.5)
            
            # 3. Enter
            kb.press_and_release("enter")
            
            # 4. Wait for load
            time.sleep(3.0)
            
            return {"success": True, "action": "browser_nav", "input": url_or_query}
            
        except Exception as e:
            log.error(f"Browser nav failed: {e}")
            return {"success": False, "error": str(e)}
