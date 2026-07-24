"""
Icon Fallback

Minimal template matching for icon-based clicking (FALLBACK ONLY).

DESIGN PHILOSOPHY:
- Use ONLY when text-based methods fail
- Support small set of critical icons
- Prefer keyboard over icon clicking
- Keep icon library minimal

This is the LAST RESORT interaction layer.
"""

from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from utils.logger import log


class IconFallback:
    """
    Template matching for icon-based clicking.

    CRITICAL NOTES:
    - This is a FALLBACK mechanism only
    - Text-based interaction should always be tried first
    - Icon library should be small and curated
    - High threshold for matches (prefer false negative)

    SUPPORTED ICONS:
    - Close button (X)
    - Minimize button (-)
    - Maximize button (□)
    - Search icon (🔍)

    QUALITY BAR:
    - Only use when text methods exhausted
    - Require high confidence (>0.8)
    - Log all icon-based clicks for review
    """

    def __init__(self, icon_dir: Path | None = None):
        """
        Initialize icon fallback.

        Args:
            icon_dir: Directory containing icon templates
        """
        self.icon_dir = icon_dir or Path("icons")
        self.match_threshold = 0.8  # High threshold for reliability

        # Icon templates (loaded lazily)
        self.templates = {}

        log.info("Icon fallback initialized (FALLBACK ONLY)")

    def find_icon(self, screen: Image.Image, icon_name: str) -> tuple[int, int] | None:
        """
        Find an icon on screen using template matching.

        Args:
            screen: Screen image
            icon_name: Name of icon template (e.g., "close_button")

        Returns:
            (x, y) position if found, None otherwise
        """
        log.warning(f"⚠️ Using ICON FALLBACK for '{icon_name}' - text-based method failed")

        # Load template
        template = self._load_template(icon_name)

        if template is None:
            log.error(f"Icon template not found: {icon_name}")
            return None

        # Convert to numpy arrays
        screen_np = np.array(screen)
        template_np = np.array(template)

        # Convert to grayscale
        screen_gray = cv2.cvtColor(screen_np, cv2.COLOR_RGB2GRAY)
        template_gray = cv2.cvtColor(template_np, cv2.COLOR_RGB2GRAY)

        # Template matching
        result = cv2.matchTemplate(screen_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val >= self.match_threshold:
            # Get center of template
            h, w = template_gray.shape
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2

            log.info(
                f"Icon found: '{icon_name}' at ({center_x}, {center_y}), confidence={max_val:.2f}"
            )
            return (center_x, center_y)

        log.warning(f"Icon not found: '{icon_name}' (best match: {max_val:.2f})")
        return None

    def _load_template(self, icon_name: str) -> Image.Image | None:
        """Load icon template from disk"""

        # Check cache
        if icon_name in self.templates:
            return self.templates[icon_name]

        # Try to load from file
        template_path = self.icon_dir / f"{icon_name}.png"

        if not template_path.exists():
            return None

        try:
            template = Image.open(template_path)
            self.templates[icon_name] = template
            return template
        except Exception as e:
            log.error(f"Failed to load icon template: {e}")
            return None

    def click_icon(self, screen: Image.Image, icon_name: str) -> bool:
        """
        Find and click an icon.

        Args:
            screen: Screen image
            icon_name: Icon to find

        Returns:
            True if clicked, False if not found
        """
        position = self.find_icon(screen, icon_name)

        if position:
            import time

            import pyautogui

            x, y = position
            pyautogui.click(x, y)
            time.sleep(0.5)

            log.info(f"🖱️ Clicked icon: {icon_name} at ({x}, {y})")
            return True

        return False


# NOTE: Icon-based clicking should be RARE
# Most interactions should use:
# 1. Keyboard shortcuts (KeyboardPolicy)
# 2. Text-anchored clicks (TextAnchorClicker)
# 3. Icon fallback (this module) - ONLY if 1 and 2 fail
