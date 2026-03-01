"""
Camera and Summary Windows

Additional UI windows for:
- Live camera feed
- Vision analysis results display
"""

import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk
from typing import Optional
import threading
from utils.logger import log

# Import camera and vision
from perception.camera_capture import get_camera
from perception.vision_analyzer import get_vision_analyzer


class CameraWindow:
    """Live camera feed window"""
    
    def __init__(self):
        """Initialize camera window"""
        self.window = ctk.CTkToplevel()
        self.window.title("📷 Live Camera")
        
        # Window settings
        self.width = 400
        self.height = 350
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        x = screen_width - self.width - 20  # Right side
        y = 100  # Top
        
        self.window.geometry(f"{self.width}x{self.height}+{x}+{y}")
        self.window.configure(fg_color="#1a1a1a")
        self.window.attributes('-topmost', True)
        
        # Camera label
        self.camera_label = ctk.CTkLabel(
            self.window,
            text="",
            fg_color="#000000"
        )
        self.camera_label.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Status
        self.status_label = ctk.CTkLabel(
            self.window,
            text="📷 Camera Active",
            font=("Segoe UI", 12),
            text_color="#00ff88"
        )
        self.status_label.pack(pady=5)
        
        # Camera instance
        self.camera = get_camera()
        self.is_running = False
        self.current_photo = None  # Store current photo
        
        # Start camera
        self.start_camera()
        
        log.info("📷 Camera window initialized")
    
    def start_camera(self):
        """Start camera feed"""
        if not self.camera.start():
            self.status_label.configure(text="❌ Camera Failed", text_color="#ff3333")
            return
        
        self.is_running = True
        # Use after() for periodic updates instead of thread
        self.window.after(33, self._update_feed)  # ~30 FPS
    
    def _update_feed(self):
        """Update camera feed (runs in main thread via after())"""
        if not self.is_running:
            return
        
        try:
            # Capture frame
            frame = self.camera.get_current_frame()
            
            if frame:
                # Resize for display
                display_size = (360, 270)
                frame_resized = frame.resize(display_size, Image.Resampling.LANCZOS)
                
                # Convert to PhotoImage
                photo = ImageTk.PhotoImage(frame_resized)
                
                # Update label
                self.camera_label.configure(image=photo)
                self.camera_label.image = photo  # Keep reference
                self.current_photo = photo
        
        except Exception as e:
            log.debug(f"Camera update: {e}")
        
        # Schedule next update
        if self.is_running:
            self.window.after(33, self._update_feed)
    
    def stop_camera(self):
        """Stop camera feed"""
        self.is_running = False
        self.camera.stop()
    
    def destroy(self):
        """Clean shutdown"""
        self.stop_camera()
        self.window.destroy()


class SummaryWindow:
    """Vision analysis summary window"""
    
    def __init__(self):
        """Initialize summary window"""
        self.window = ctk.CTkToplevel()
        self.window.title("🔍 Vision Analysis")
        
        # Window settings
        self.width = 450
        self.height = 400
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        x = screen_width - self.width - 20  # Right side
        y = 460  # Below camera
        
        self.window.geometry(f"{self.width}x{self.height}+{x}+{y}")
        self.window.configure(fg_color="#1a1a1a")
        self.window.attributes('-topmost', True)
        
        # Header
        header = ctk.CTkLabel(
            self.window,
            text="🔍 Vision Analysis Summary",
            font=("Segoe UI", 16, "bold"),
            text_color="#3366ff"
        )
        header.pack(pady=10)
        
        # Summary text box
        self.summary_box = ctk.CTkTextbox(
            self.window,
            font=("Segoe UI", 13),
            fg_color="#0a0a0a",
            text_color="#ffffff",
            wrap="word",
            activate_scrollbars=True
        )
        self.summary_box.pack(fill="both", expand=True, padx=15, pady=(0, 10))
        
        # Initial text
        self.set_summary("✨ Ready for vision queries!\n\nAsk me questions like:\n• What do you see?\n• Who is in the camera?\n• What am I wearing?\n• Describe what's in front of you")
        
        # Analyze button
        self.analyze_btn = ctk.CTkButton(
            self.window,
            text="🔍 Analyze Now",
            command=self.quick_analyze,
            font=("Segoe UI", 13, "bold"),
            fg_color="#3366ff",
            hover_color="#2952cc",
            height=40
        )
        self.analyze_btn.pack(pady=(0, 10), padx=15, fill="x")
        
        log.info("🔍 Summary window initialized")
    
    def set_summary(self, text: str):
        """Update summary text"""
        self.summary_box.configure(state="normal")
        self.summary_box.delete("1.0", "end")
        self.summary_box.insert("1.0", text)
        self.summary_box.configure(state="disabled")
    
    def append_summary(self, text: str):
        """Append to summary"""
        self.summary_box.configure(state="normal")
        self.summary_box.insert("end", f"\n\n{text}")
        self.summary_box.configure(state="disabled")
        self.summary_box.see("end")  # Scroll to bottom
    
    def quick_analyze(self):
        """Quick analyze button - analyze current frame"""
        def analyze_thread():
            try:
                self.analyze_btn.configure(text="⏳ Analyzing...", state="disabled")
                self.set_summary("⏳ Analyzing camera feed...\n\nThis may take a few seconds...")
                
                # Get camera frame
                camera = get_camera()
                frame = camera.get_current_frame()
                
                if not frame:
                    self.set_summary("❌ Error: Could not capture camera frame")
                    return
                
                # Analyze with vision
                analyzer = get_vision_analyzer()
                result = analyzer.detect_person(frame)
                
                # Format result
                if result["person_detected"]:
                    if result["is_divyanshu"]:
                        summary = f"👤 **DIVYANSHU DETECTED!**\n\n{result['description']}"
                    else:
                        summary = f"👤 Person Detected\n\n{result['description']}"
                else:
                    summary = f"No person detected\n\n{result['description']}"
                
                self.set_summary(summary)
                
            except Exception as e:
                self.set_summary(f"❌ Error: {str(e)}")
                log.error(f"Quick analyze failed: {e}")
            
            finally:
                self.analyze_btn.configure(text="🔍 Analyze Now", state="normal")
        
        # Run in background
        threading.Thread(target=analyze_thread, daemon=True).start()
    
    def destroy(self):
        """Clean shutdown"""
        self.window.destroy()


class CameraUIManager:
    """Manages camera and summary windows"""
    
    def __init__(self):
        """Initialize manager"""
        self.camera_window: Optional[CameraWindow] = None
        self.summary_window: Optional[SummaryWindow] = None
        self.is_active = False
    
    def start(self):
        """Start both windows"""
        if self.is_active:
            return
        
        try:
            self.camera_window = CameraWindow()
            self.summary_window = SummaryWindow()
            self.is_active = True
            log.info("✅ Camera UI manager started")
        except Exception as e:
            log.error(f"Failed to start camera UI: {e}")
    
    def stop(self):
        """Stop both windows"""
        if self.camera_window:
            self.camera_window.destroy()
        if self.summary_window:
            self.summary_window.destroy()
        self.is_active = False
    
    def update_summary(self, text: str):
        """Update summary text"""
        if self.summary_window:
            self.summary_window.set_summary(text)
    
    def append_summary(self, text: str):
        """Append to summary"""
        if self.summary_window:
            self.summary_window.append_summary(text)


# Global manager
_camera_ui = None


def get_camera_ui() -> CameraUIManager:
    """Get or create camera UI manager"""
    global _camera_ui
    if _camera_ui is None:
        _camera_ui = CameraUIManager()
    return _camera_ui
