"""
Keyboard Policy

Keyboard-first interaction strategies for reliable UI automation.

DESIGN PHILOSOPHY:
- KEYBOARD > MOUSE (always)
- Use universal shortcuts when possible
- Context-aware navigation (browser vs editor vs terminal)
- Fallback gracefully if keyboard fails

This is the PRIMARY INTERACTION LAYER - avoids blind clicking.
"""

import time
from dataclasses import dataclass

import keyboard as kb

from perception.ui_state_builder import AppType, UIState
from utils.logger import log


@dataclass
class KeyboardAction:
    """Represents a keyboard action with context"""

    keys: str  # e.g., "ctrl+n", "tab", "enter"
    description: str
    context: str  # browser, editor, universal, etc.
    delay_after: float = 0.3  # Seconds to wait after action


class KeyboardPolicy:
    """
    Implements keyboard-first interaction strategies.

    CORE RESPONSIBILITIES:
    1. Provide context-aware keyboard shortcuts
    2. Navigate UIs using keyboard (Tab, Enter, Arrow keys)
    3. Fill forms using keyboard navigation
    4. Avoid mouse clicks when possible

    INTERACTION HIERARCHY:
    1. Universal shortcuts (work everywhere)
       - Ctrl+C, Ctrl+V, Ctrl+S, Ctrl+N, etc.

    2. Context-specific shortcuts
       - Browser: Ctrl+T, Ctrl+L, Ctrl+W
       - Editor: Ctrl+F, Ctrl+H, Ctrl+G
       - Terminal: Ctrl+C, Ctrl+D, Ctrl+Z

    3. Navigation keys
       - Tab, Shift+Tab (form navigation)
       - Enter (submit/activate)
       - Arrow keys (menu navigation)

    4. Fallback to mouse (if keyboard fails)

    QUALITY BAR:
    - Deterministic (same context = same keys)
    - Fast (no waiting for UI elements)
    - Reliable (works across OS versions)
    """

    def __init__(self):
        """Initialize keyboard policy"""
        self.default_delay = 0.3  # Default delay after keypress
        self.long_delay = 0.8  # For actions that trigger UI changes

        log.info("Keyboard policy initialized")

    # ==================== UNIVERSAL ACTIONS ====================

    def new_file(self) -> KeyboardAction:
        """Create new file (Ctrl+N)"""
        return KeyboardAction(
            keys="ctrl+n", description="New file", context="universal", delay_after=self.long_delay
        )

    def save_file(self) -> KeyboardAction:
        """Save file (Ctrl+S)"""
        return KeyboardAction(
            keys="ctrl+s",
            description="Save file",
            context="universal",
            delay_after=self.default_delay,
        )

    def open_file(self) -> KeyboardAction:
        """Open file dialog (Ctrl+O)"""
        return KeyboardAction(
            keys="ctrl+o", description="Open file", context="universal", delay_after=self.long_delay
        )

    def copy(self) -> KeyboardAction:
        """Copy (Ctrl+C)"""
        return KeyboardAction(keys="ctrl+c", description="Copy", context="universal")

    def paste(self) -> KeyboardAction:
        """Paste (Ctrl+V)"""
        return KeyboardAction(keys="ctrl+v", description="Paste", context="universal")

    def select_all(self) -> KeyboardAction:
        """Select all (Ctrl+A)"""
        return KeyboardAction(keys="ctrl+a", description="Select all", context="universal")

    def undo(self) -> KeyboardAction:
        """Undo (Ctrl+Z)"""
        return KeyboardAction(keys="ctrl+z", description="Undo", context="universal")

    # ==================== BROWSER ACTIONS ====================

    def new_tab(self) -> KeyboardAction:
        """Open new browser tab (Ctrl+T)"""
        return KeyboardAction(
            keys="ctrl+t", description="New tab", context="browser", delay_after=self.long_delay
        )

    def close_tab(self) -> KeyboardAction:
        """Close current tab (Ctrl+W)"""
        return KeyboardAction(keys="ctrl+w", description="Close tab", context="browser")

    def focus_address_bar(self) -> KeyboardAction:
        """Focus browser address bar (Ctrl+L)"""
        return KeyboardAction(keys="ctrl+l", description="Focus address bar", context="browser")

    def reload_page(self) -> KeyboardAction:
        """Reload page (Ctrl+R)"""
        return KeyboardAction(
            keys="ctrl+r", description="Reload page", context="browser", delay_after=self.long_delay
        )

    # ==================== EDITOR ACTIONS ====================

    def find(self) -> KeyboardAction:
        """Open find dialog (Ctrl+F)"""
        return KeyboardAction(
            keys="ctrl+f", description="Find", context="editor", delay_after=self.default_delay
        )

    def replace(self) -> KeyboardAction:
        """Open replace dialog (Ctrl+H)"""
        return KeyboardAction(
            keys="ctrl+h", description="Replace", context="editor", delay_after=self.default_delay
        )

    def go_to_line(self) -> KeyboardAction:
        """Go to line (Ctrl+G)"""
        return KeyboardAction(
            keys="ctrl+g",
            description="Go to line",
            context="editor",
            delay_after=self.default_delay,
        )

    # ==================== NAVIGATION ACTIONS ====================

    def tab_forward(self) -> KeyboardAction:
        """Tab to next field"""
        return KeyboardAction(keys="tab", description="Tab forward", context="navigation")

    def tab_backward(self) -> KeyboardAction:
        """Tab to previous field (Shift+Tab)"""
        return KeyboardAction(keys="shift+tab", description="Tab backward", context="navigation")

    def press_enter(self) -> KeyboardAction:
        """Press Enter (submit form, activate button)"""
        return KeyboardAction(
            keys="enter",
            description="Press Enter",
            context="navigation",
            delay_after=self.long_delay,
        )

    def press_escape(self) -> KeyboardAction:
        """Press Escape (cancel, close dialog)"""
        return KeyboardAction(keys="esc", description="Press Escape", context="navigation")

    def arrow_down(self) -> KeyboardAction:
        """Arrow down"""
        return KeyboardAction(keys="down", description="Arrow down", context="navigation")

    def arrow_up(self) -> KeyboardAction:
        """Arrow up"""
        return KeyboardAction(keys="up", description="Arrow up", context="navigation")

    # ==================== EXECUTION ====================

    def execute(self, action: KeyboardAction):
        """
        Execute a keyboard action.

        Args:
            action: KeyboardAction to execute
        """
        log.info(f"⌨️ Keyboard: {action.description} ({action.keys})")

        try:
            kb.press_and_release(action.keys)
            time.sleep(action.delay_after)
        except Exception as e:
            log.error(f"Keyboard action failed: {e}")
            raise

    # ==================== SMART ACTIONS (CONTEXT-AWARE) ====================

    def smart_new_document(self, ui_state: UIState) -> KeyboardAction:
        """
        Create new document based on context.

        - Browser → New tab
        - Editor → New file
        - Unknown → Ctrl+N
        """
        if ui_state.browser_open or ui_state.app_type == AppType.BROWSER:
            return self.new_tab()
        else:
            return self.new_file()

    def smart_search(self, ui_state: UIState) -> KeyboardAction:
        """
        Initiate search based on context.

        - Browser → Focus address bar
        - Editor → Open find dialog
        - Unknown → Ctrl+F
        """
        if ui_state.browser_open or ui_state.app_type == AppType.BROWSER:
            return self.focus_address_bar()
        else:
            return self.find()

    def navigate_form(self, direction: str = "forward") -> KeyboardAction:
        """
        Navigate form fields.

        Args:
            direction: "forward" or "backward"
        """
        if direction == "backward":
            return self.tab_backward()
        else:
            return self.tab_forward()

    def submit_form(self) -> KeyboardAction:
        """Submit current form"""
        return self.press_enter()

    # ==================== TEXT ENTRY ====================

    def type_text(self, text: str, delay: float = 0.05):
        """
        Type text using keyboard.

        Args:
            text: Text to type
            delay: Delay between characters
        """
        log.info(f"⌨️ Typing: {text[:50]}...")

        try:
            kb.write(text, delay=delay)
            time.sleep(self.default_delay)
        except Exception as e:
            log.error(f"Text typing failed: {e}")
            raise

    # ==================== FORM FILLING STRATEGY ====================

    def fill_form_field(self, value: str, navigate_next: bool = True):
        """
        Fill a form field and optionally navigate to next.

        Strategy:
        1. Clear existing value (Ctrl+A)
        2. Type new value
        3. Tab to next field (if navigate_next)

        Args:
            value: Value to enter
            navigate_next: Whether to tab to next field
        """
        log.info(f"📝 Filling field: {value[:30]}...")

        # Clear field
        self.execute(self.select_all())

        # Type value
        self.type_text(value)

        # Navigate to next
        if navigate_next:
            self.execute(self.tab_forward())
