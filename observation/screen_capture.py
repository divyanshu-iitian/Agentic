"""
Screen Capture and OCR

Captures screenshots and extracts text using OCR.
"""

import io
from pathlib import Path
from typing import Optional
from datetime import datetime
import pyautogui
from PIL import Image
from utils.logger import log

# EasyOCR is heavy, only import if needed
_ocr_reader = None


def get_ocr_reader():
    """Lazy load OCR reader"""
    global _ocr_reader
    if _ocr_reader is None:
        try:
            import easyocr
            from core.config import get_config
            config = get_config()
            langs = config.observation.ocr_languages
            _ocr_reader = easyocr.Reader(langs, gpu=False)
            log.info(f"OCR reader initialized: {langs}")
        except Exception as e:
            log.error(f"Failed to initialize OCR: {e}")
            _ocr_reader = None
    return _ocr_reader


class ScreenCapture:
    """Screen capture and OCR functionality"""
    
    def __init__(self):
        self.screenshot_dir = Path("screenshots")
        self.screenshot_dir.mkdir(exist_ok=True)
        log.info("Screen capture initialized")
    
    def capture(self, save: bool = False) -> Image.Image:
        """
        Capture screenshot.
        
        Args:
            save: Whether to save to file
            
        Returns:
            PIL Image object
        """
        screenshot = pyautogui.screenshot()
        
        if save:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = self.screenshot_dir / f"capture_{timestamp}.png"
            screenshot.save(filepath)
            log.info(f"Screenshot saved: {filepath}")
        
        return screenshot
    
    def capture_region(self, x: int, y: int, width: int, height: int) -> Image.Image:
        """Capture specific screen region"""
        screenshot = pyautogui.screenshot(region=(x, y, width, height))
        return screenshot
    
    def extract_text(self, image: Optional[Image.Image] = None) -> str:
        """
        Extract text from image using OCR.
        
        Args:
            image: PIL Image (if None, captures screen)
            
        Returns:
            Extracted text
        """
        from core.config import get_config
        config = get_config()
        
        if not config.observation.ocr_enabled:
            return ""
        
        reader = get_ocr_reader()
        if reader is None:
            return ""
        
        if image is None:
            image = self.capture()
        
        try:
            # Convert PIL Image to numpy array
            import numpy as np
            img_array = np.array(image)
            
            # Run OCR
            results = reader.readtext(img_array)
            
            # Extract text
            text_lines = [text for (_, text, _) in results]
            extracted_text = "\n".join(text_lines)
            
            log.info(f"OCR extracted {len(text_lines)} text blocks")
            return extracted_text
            
        except Exception as e:
            log.error(f"OCR failed: {e}")
            return ""
    
    def get_screen_description(self) -> str:
        """
        Get a simple description of current screen state.
        
        Returns:
            Text description
        """
        # Capture screenshot
        screenshot = self.capture()
        
        # Get screen size
        width, height = screenshot.size
        
        # Extract text
        text = self.extract_text(screenshot)
        
        description = f"Screen: {width}x{height}\n"
        if text:
            description += f"Visible text:\n{text[:500]}"
        else:
            description += "No text detected"
        
        return description
