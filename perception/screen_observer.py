"""
Screen Observer

Captures screen state with timestamps and comparison capability.

DESIGN PHILOSOPHY:
- Capture full screen or active window
- Support before/after observation comparison
- Provide raw pixels for downstream processing
- Keep captures lightweight and cacheable

This is the INPUT LAYER of perception - it provides raw visual data.
"""

import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple
from dataclasses import dataclass
import pyautogui
from PIL import Image
from utils.logger import log


@dataclass
class ScreenObservation:
    """Immutable screen observation with metadata"""
    
    image: Image.Image
    timestamp: float
    width: int
    height: int
    observation_id: str
    
    def save(self, path: Path):
        """Save observation to disk"""
        self.image.save(path)
        log.debug(f"Saved observation {self.observation_id} to {path}")
    
    def to_bytes(self) -> bytes:
        """Convert to bytes for hashing/comparison"""
        import io
        buf = io.BytesIO()
        self.image.save(buf, format='PNG')
        return buf.getvalue()


class ScreenObserver:
    """
    Captures and manages screen observations.
    
    CORE RESPONSIBILITIES:
    1. Capture screen at any moment
    2. Store observations with timestamps
    3. Provide before/after comparison capability
    4. Support both full screen and active window capture
    
    DESIGN NOTES:
    - Does NOT perform OCR (that's ocr_extractor's job)
    - Does NOT interpret content (that's ui_state_builder's job)
    - ONLY captures raw visual state
    """
    
    def __init__(self, save_observations: bool = False, output_dir: Optional[Path] = None):
        """
        Initialize screen observer.
        
        Args:
            save_observations: Whether to save observations to disk
            output_dir: Directory for saved observations
        """
        self.save_observations = save_observations
        self.output_dir = output_dir or Path("screenshots")
        
        if self.save_observations:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Observation cache (for before/after comparison)
        self.last_observation: Optional[ScreenObservation] = None
        self.observation_count = 0
        
        log.info(f"Screen observer initialized (save={save_observations})")
    
    def observe(self, region: Optional[Tuple[int, int, int, int]] = None) -> ScreenObservation:
        """
        Capture current screen state.
        
        Args:
            region: Optional (x, y, width, height) for partial capture
        
        Returns:
            ScreenObservation object
        """
        try:
            # Capture screen
            if region:
                screenshot = pyautogui.screenshot(region=region)
            else:
                screenshot = pyautogui.screenshot()
            
            # Create observation
            self.observation_count += 1
            obs_id = f"obs_{self.observation_count}_{int(time.time())}"
            
            observation = ScreenObservation(
                image=screenshot,
                timestamp=time.time(),
                width=screenshot.width,
                height=screenshot.height,
                observation_id=obs_id
            )
            
            # Save if enabled
            if self.save_observations:
                save_path = self.output_dir / f"{obs_id}.png"
                observation.save(save_path)
            
            # Cache for comparison
            self.last_observation = observation
            
            log.debug(f"Captured observation {obs_id} ({observation.width}x{observation.height})")
            return observation
            
        except Exception as e:
            log.error(f"Screen capture failed: {e}")
            raise
    
    def observe_before_after(self, action_fn, delay: float = 0.5) -> Tuple[ScreenObservation, ScreenObservation]:
        """
        Capture screen before and after an action.
        
        Args:
            action_fn: Function to execute between observations
            delay: Seconds to wait after action before capturing
        
        Returns:
            (before, after) observation tuple
        """
        before = self.observe()
        
        # Execute action
        action_fn()
        
        # Wait for UI to update
        time.sleep(delay)
        
        after = self.observe()
        
        return before, after
    
    def get_screen_size(self) -> Tuple[int, int]:
        """Get current screen dimensions"""
        size = pyautogui.size()
        return size.width, size.height
    
    def compare_observations(self, obs1: ScreenObservation, obs2: ScreenObservation) -> dict:
        """
        Compare two observations (basic pixel-level comparison).
        
        This is a COARSE comparison. Fine-grained semantic comparison
        is handled by change_detector.py.
        
        Args:
            obs1: First observation
            obs2: Second observation
        
        Returns:
            Comparison metrics
        """
        import hashlib
        
        # Quick hash comparison
        hash1 = hashlib.md5(obs1.to_bytes()).hexdigest()
        hash2 = hashlib.md5(obs2.to_bytes()).hexdigest()
        
        identical = hash1 == hash2
        
        # Calculate pixel difference percentage if not identical
        pixel_diff_pct = 0.0
        if not identical:
            # Sample-based comparison for speed
            import numpy as np
            arr1 = np.array(obs1.image.resize((100, 100)))  # Downsample for speed
            arr2 = np.array(obs2.image.resize((100, 100)))
            
            diff = np.abs(arr1.astype(float) - arr2.astype(float))
            pixel_diff_pct = (diff > 10).sum() / diff.size * 100  # 10 = threshold
        
        return {
            "identical": identical,
            "hash1": hash1,
            "hash2": hash2,
            "pixel_diff_pct": round(pixel_diff_pct, 2),
            "time_delta": obs2.timestamp - obs1.timestamp
        }
