"""
Text Anchor Clicker

OCR-based text-anchored clicking for reliable UI interaction.

DESIGN PHILOSOPHY:
- NEVER click arbitrary coordinates
- ALWAYS use text as anchor
- Calculate click positions relative to text
- Provide confidence scores

This is the INTELLIGENT CLICKING LAYER - no blind mouse actions.
"""

import time
from dataclasses import dataclass

import pyautogui

from perception.ocr_extractor import TextElement
from utils.logger import log


@dataclass
class ClickTarget:
    """Represents a click target with context"""

    text_anchor: str
    click_position: tuple[int, int]  # (x, y)
    confidence: float
    strategy: str  # "exact_match", "partial_match", "near_label", etc.
    element: TextElement | None = None

    def __str__(self) -> str:
        x, y = self.click_position
        return (
            f"Click '{self.text_anchor}' at ({x}, {y}) - "
            f"{self.strategy} (conf={self.confidence:.2f})"
        )


class TextAnchorClicker:
    """
    Performs clicks anchored to detected text.

    CORE RESPONSIBILITIES:
    1. Find text elements by query
    2. Calculate safe click positions
    3. Click buttons/links by text
    4. Click input fields near labels
    5. Provide confidence scores

    CLICKING STRATEGIES:

    1. BUTTON/LINK CLICKING
       - Find exact text match
       - Click center of text bounding box
       - High confidence

    2. INPUT FIELD CLICKING (near label)
       - Find label text
       - Infer input position (right or below label)
       - Click estimated input position
       - Medium confidence

    3. ICON CLICKING (fallback only)
       - Use template matching
       - Low confidence
       - Requires icon library

    QUALITY BAR:
    - Precision > Recall (better to not click than mis-click)
    - Always log click reasoning
    - Provide fallback if text not found
    """

    def __init__(self):
        """Initialize text anchor clicker"""
        self.click_delay = 0.5  # Delay after click
        self.double_click_interval = 0.3  # Interval for double-click

        log.info("Text anchor clicker initialized")

    # ==================== TEXT FINDING ====================

    def find_text_target(
        self, text_elements: list[TextElement], query: str, exact: bool = False
    ) -> ClickTarget | None:
        """
        Find a clickable text element.

        Args:
            text_elements: List of detected text elements
            query: Text to find (e.g., "Submit", "Login", "Search")
            exact: Whether to require exact match

        Returns:
            ClickTarget if found, None otherwise
        """
        query_lower = query.lower()

        # Try exact match first
        for elem in text_elements:
            elem_lower = elem.text.lower()

            if exact:
                if elem_lower == query_lower:
                    return self._create_button_target(elem, "exact_match")
            else:
                if query_lower in elem_lower:
                    return self._create_button_target(elem, "partial_match")

        log.warning(f"Text not found: '{query}'")
        return None

    def find_button(self, text_elements: list[TextElement], button_text: str) -> ClickTarget | None:
        """
        Find a button by text.

        Common button texts:
        - "Submit", "Send", "Login", "Sign In", "Search", etc.

        Args:
            text_elements: List of detected text elements
            button_text: Button text to find

        Returns:
            ClickTarget for button
        """
        # Buttons are often short text
        short_elements = [elem for elem in text_elements if len(elem.text.split()) <= 3]

        target = self.find_text_target(short_elements, button_text, exact=False)

        if target:
            log.info(f"Found button: {target}")

        return target

    def find_link(self, text_elements: list[TextElement], link_text: str) -> ClickTarget | None:
        """
        Find a link by text.

        Args:
            text_elements: List of detected text elements
            link_text: Link text to find

        Returns:
            ClickTarget for link
        """
        return self.find_text_target(text_elements, link_text, exact=False)

    def find_input_field_near_label(
        self, text_elements: list[TextElement], label_text: str
    ) -> ClickTarget | None:
        """
        Find an input field by finding its label.

        Strategy:
        1. Find label text
        2. Infer input position (typically right or below)
        3. Return click target for inferred position

        Args:
            text_elements: List of detected text elements
            label_text: Label text (e.g., "Email", "Password", "Name")

        Returns:
            ClickTarget for input field
        """
        # Find label
        label_lower = label_text.lower()
        label_elem = None

        for elem in text_elements:
            if label_lower in elem.text.lower():
                label_elem = elem
                break

        if not label_elem:
            log.warning(f"Label not found: '{label_text}'")
            return None

        # Infer input position
        # Strategy 1: Look for input field to the right
        right_position = self._infer_input_right_of_label(label_elem, text_elements)

        if right_position:
            return ClickTarget(
                text_anchor=f"Input near '{label_elem.text}'",
                click_position=right_position,
                confidence=0.7,
                strategy="input_right_of_label",
                element=label_elem,
            )

        # Strategy 2: Input field below label
        below_position = self._infer_input_below_label(label_elem)

        return ClickTarget(
            text_anchor=f"Input near '{label_elem.text}'",
            click_position=below_position,
            confidence=0.6,
            strategy="input_below_label",
            element=label_elem,
        )

    # ==================== POSITION INFERENCE ====================

    def _create_button_target(self, elem: TextElement, strategy: str) -> ClickTarget:
        """Create click target for a button/link"""
        x, y = elem.center

        return ClickTarget(
            text_anchor=elem.text,
            click_position=(x, y),
            confidence=0.9,
            strategy=strategy,
            element=elem,
        )

    def _infer_input_right_of_label(
        self, label: TextElement, all_elements: list[TextElement]
    ) -> tuple[int, int] | None:
        """
        Infer input field position to the right of label.

        Look for empty space or another element that could be an input.
        """
        # Check if there's likely an input to the right
        # (no other text immediately to the right = likely input field)

        label_x, label_y, label_w, label_h = label.box
        label_right = label_x + label_w

        # Check for elements to the right
        elements_to_right = [
            elem for elem in all_elements if elem.is_right_of(label, max_distance=300)
        ]

        if not elements_to_right:
            # No text to the right = likely input field
            # Click slightly to the right of label
            input_x = label_right + 100  # 100px to the right
            input_y = label_y + (label_h // 2)  # Vertically aligned

            return (input_x, input_y)

        return None

    def _infer_input_below_label(self, label: TextElement) -> tuple[int, int]:
        """
        Infer input field position below label.

        Common in vertical form layouts.
        """
        label_x, label_y, label_w, label_h = label.box

        # Input typically 30-50px below label
        input_x = label_x + (label_w // 2)  # Horizontally aligned with label
        input_y = label_y + label_h + 35  # 35px below

        return (input_x, input_y)

    # ==================== CLICKING EXECUTION ====================

    def click(self, target: ClickTarget, double: bool = False):
        """
        Execute a click at the target position.

        Args:
            target: ClickTarget to click
            double: Whether to double-click
        """
        x, y = target.click_position

        log.info(f"🖱️ Clicking: {target}")

        try:
            if double:
                pyautogui.doubleClick(x, y, interval=self.double_click_interval)
            else:
                pyautogui.click(x, y)

            time.sleep(self.click_delay)

        except Exception as e:
            log.error(f"Click failed: {e}")
            raise

    def click_button(self, text_elements: list[TextElement], button_text: str) -> bool:
        """
        Find and click a button by text.

        Args:
            text_elements: List of detected text elements
            button_text: Button text to find

        Returns:
            True if clicked, False if not found
        """
        target = self.find_button(text_elements, button_text)

        if not target:
            return False

        self.click(target)
        return True

    def click_link(self, text_elements: list[TextElement], link_text: str) -> bool:
        """
        Find and click a link by text.

        Args:
            text_elements: List of detected text elements
            link_text: Link text to find

        Returns:
            True if clicked, False if not found
        """
        target = self.find_link(text_elements, link_text)

        if not target:
            return False

        self.click(target)
        return True

    def click_input_field(self, text_elements: list[TextElement], label_text: str) -> bool:
        """
        Find and click an input field by its label.

        Args:
            text_elements: List of detected text elements
            label_text: Label text (e.g., "Email", "Password")

        Returns:
            True if clicked, False if not found
        """
        target = self.find_input_field_near_label(text_elements, label_text)

        if not target:
            return False

        # Input fields often need focus click
        self.click(target)
        return True
