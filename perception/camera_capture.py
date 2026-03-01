"""
Camera Capture Module

Captures live camera feed for vision-based queries.
Supports:
- Real-time webcam capture
- Frame analysis
- Person detection (custom recognition)
"""

import cv2
import numpy as np
from PIL import Image
from typing import Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from utils.logger import log


@dataclass
class CameraFrame:
    """A single camera frame with metadata."""
    image: Image.Image
    timestamp: datetime
    frame_id: int
    resolution: Tuple[int, int]
    
    def save(self, path: Path):
        """Save frame to disk."""
        self.image.save(path)


class CameraCapture:
    """
    Webcam capture for vision queries.
    
    Features:
    - Live camera feed
    - Frame capture on demand
    - Auto-start on agent init
    """
    
    def __init__(self, camera_id: int = 0, auto_start: bool = True):
        """
        Initialize camera capture.
        
        Args:
            camera_id: Camera device ID (0 for default webcam)
            auto_start: Automatically start camera on init
        """
        self.camera_id = camera_id
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_active = False
        self.frame_count = 0
        
        # Storage
        self.cache_dir = Path("screenshots/camera_frames")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        if auto_start:
            self.start()
    
    def start(self) -> bool:
        """
        Start camera capture.
        
        Returns:
            True if started successfully
        """
        if self.is_active:
            log.warning("Camera already active")
            return True
        
        try:
            self.cap = cv2.VideoCapture(self.camera_id)
            
            if not self.cap.isOpened():
                log.error(f"Failed to open camera {self.camera_id}")
                return False
            
            # Set camera properties for better quality
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            
            self.is_active = True
            log.info(f"📷 Camera {self.camera_id} started successfully")
            return True
        
        except Exception as e:
            log.error(f"Camera start failed: {e}")
            return False
    
    def stop(self):
        """Stop camera capture."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        
        self.is_active = False
        log.info("📷 Camera stopped")
    
    def capture_frame(self, save: bool = True) -> Optional[CameraFrame]:
        """
        Capture current camera frame.
        
        Args:
            save: Save frame to disk
        
        Returns:
            CameraFrame or None if capture failed
        """
        if not self.is_active:
            log.warning("Camera not active, starting...")
            if not self.start():
                return None
        
        try:
            ret, frame = self.cap.read()
            
            if not ret:
                log.error("Failed to read camera frame")
                return None
            
            # Convert BGR (OpenCV) to RGB (PIL)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Create PIL Image
            pil_image = Image.fromarray(frame_rgb)
            
            # Resolution
            height, width = frame.shape[:2]
            resolution = (width, height)
            
            # Create CameraFrame
            self.frame_count += 1
            camera_frame = CameraFrame(
                image=pil_image,
                timestamp=datetime.now(),
                frame_id=self.frame_count,
                resolution=resolution
            )
            
            # Save if requested
            if save:
                filename = f"camera_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.frame_count}.png"
                save_path = self.cache_dir / filename
                camera_frame.save(save_path)
                log.debug(f"Camera frame saved: {save_path}")
            
            return camera_frame
        
        except Exception as e:
            log.error(f"Frame capture failed: {e}")
            return None
    
    def get_current_frame(self) -> Optional[Image.Image]:
        """Get current frame as PIL Image (no save)."""
        frame = self.capture_frame(save=False)
        return frame.image if frame else None
    
    def __del__(self):
        """Cleanup on deletion."""
        self.stop()


# Global camera instance
_camera = None


def get_camera() -> CameraCapture:
    """Get or create global camera instance."""
    global _camera
    if _camera is None:
        _camera = CameraCapture(auto_start=False)  # Don't auto-start, start manually
    return _camera


def start_camera():
    """Start the global camera."""
    camera = get_camera()
    return camera.start()


def capture_camera_frame() -> Optional[CameraFrame]:
    """Capture frame from global camera."""
    camera = get_camera()
    return camera.capture_frame()


def stop_camera():
    """Stop the global camera."""
    camera = get_camera()
    camera.stop()
