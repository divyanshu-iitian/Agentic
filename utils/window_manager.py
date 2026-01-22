
import ctypes
from typing import Optional
from utils.logger import log

def get_active_window_title() -> Optional[str]:
    """
    Get the title of the currently active (foreground) window.
    Reliable ground truth for "Active App".
    """
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        
        # Get title length
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return None
            
        # Get title
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        title = buff.value
        
        return title
    except Exception as e:
        log.error(f"Failed to get active window: {e}")
        return None

def is_app_active(app_name_fragment: str) -> bool:
    """Check if an app with the given name fragment is active"""
    title = get_active_window_title()
    if not title:
        return False
    return app_name_fragment.lower() in title.lower()
