"""
Premium Floating Input Box UI - Next Generation

Modern, beautiful interface with:
- Glassmorphism effects
- Smooth animations
- Status indicators
- Activity visualization
- Premium color schemes
"""

import customtkinter as ctk
import tkinter as tk
from typing import Callable, Optional
from core.config import get_config
from utils.logger import log
import threading
import time

# Set premium theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class PremiumFloatingUI:
    """Next-gen floating UI with premium design"""
    
    def __init__(self, on_command: Callable[[str], None]):
        """Initialize premium UI"""
        self.on_command = on_command
        config = get_config()
        
        # Main Window
        self.root = ctk.CTk()
        self.root.title("Agentic AI")
        
        # 🎨 Premium Window Settings
        self.root.overrideredirect(True)  # Borderless
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.97)  # Glass effect
        
        # Geometry (Centered Top)
        self.width = 750
        self.height = 90
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (self.width // 2)
        y = int(screen_height * 0.12)  # 12% from top
        
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")
        self.root.configure(fg_color="#0a0a0a")  # Deep black
        
        # Draggable
        self.root.bind("<ButtonPress-1>", self.start_move)
        self.root.bind("<ButtonRelease-1>", self.stop_move)
        self.root.bind("<B1-Motion>", self.do_move)
        
        # State
        self.feedback_mode = False
        self.is_running = False
        self.activity_animation = False
        
        # Build UI
        self._build_ui()
        
        # Focus
        self.root.after(100, self.focus)
        
        log.info("✨ Premium UI initialized")

    def _build_ui(self):
        """Build premium UI components"""
        
        # === Main Container with Gradient Border ===
        self.main_frame = ctk.CTkFrame(
            self.root,
            fg_color=("#1a1a1a", "#1a1a1a"),
            corner_radius=20,
            border_width=2,
            border_color=("#3366ff", "#3366ff")  # Blue glow
        )
        self.main_frame.pack(fill="both", expand=True, padx=3, pady=3)
        
        # === Top Bar (Status + Controls) ===
        self.top_bar = ctk.CTkFrame(
            self.main_frame,
            fg_color="transparent",
            height=25
        )
        self.top_bar.pack(fill="x", padx=15, pady=(8, 0))
        
        # Status Indicator (Left)
        self.status_dot = ctk.CTkLabel(
            self.top_bar,
            text="●",
            font=("Segoe UI", 12),
            text_color="#00ff88"  # Green = Ready
        )
        self.status_dot.pack(side="left")
        
        self.status_label = ctk.CTkLabel(
            self.top_bar,
            text="Ready",
            font=("Segoe UI", 10),
            text_color="#888888"
        )
        self.status_label.pack(side="left", padx=(5, 0))
        
        # Activity Indicator (Animated)
        self.activity_label = ctk.CTkLabel(
            self.top_bar,
            text="",
            font=("Segoe UI", 10),
            text_color="#3366ff"
        )
        self.activity_label.pack(side="left", padx=(10, 0))
        
        # Close Button (Right)
        self.btn_close = ctk.CTkButton(
            self.top_bar,
            text="×",
            width=20,
            height=20,
            font=("Segoe UI", 16, "bold"),
            fg_color="transparent",
            hover_color="#ff3333",
            text_color="#666666",
            corner_radius=10,
            command=self._on_escape
        )
        self.btn_close.pack(side="right")
        
        # === Input Area ===
        self.input_frame = ctk.CTkFrame(
            self.main_frame,
            fg_color="transparent"
        )
        self.input_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        
        # Icon
        self.icon_label = ctk.CTkLabel(
            self.input_frame,
            text="🤖",
            font=("Segoe UI Emoji", 28)
        )
        self.icon_label.pack(side="left", padx=(10, 8))
        
        # Input Field
        self.entry = ctk.CTkEntry(
            self.input_frame,
            placeholder_text="What would you like me to do?",
            font=("Segoe UI", 15),
            height=50,
            fg_color="#0f0f0f",
            text_color="#ffffff",
            placeholder_text_color="#555555",
            border_width=0,
            corner_radius=12
        )
        self.entry.pack(side="left", fill="both", expand=True, padx=5)
        self.entry.bind("<Return>", self._on_enter)
        self.entry.bind("<Escape>", self._on_escape)
        
        # === Action Buttons ===
        self.buttons_frame = ctk.CTkFrame(
            self.input_frame,
            fg_color="transparent"
        )
        self.buttons_frame.pack(side="right", padx=(5, 10))
        
        # Teach Button
        self.btn_teach = ctk.CTkButton(
            self.buttons_frame,
            text="🧠",
            width=45,
            height=45,
            font=("Segoe UI Emoji", 16),
            fg_color="#2a2a2a",
            hover_color="#3d3d3d",
            corner_radius=12,
            command=self._toggle_teach_mode
        )
        self.btn_teach.pack(side="left", padx=3)
        
        # Main Action Button
        self.btn_action = ctk.CTkButton(
            self.buttons_frame,
            text="▶",
            width=80,
            height=45,
            font=("Segoe UI", 18),
            fg_color=("#0066ff", "#0052cc"),
            hover_color=("#0052cc", "#0041a3"),
            corner_radius=12,
            command=self._on_submit
        )
        self.btn_action.pack(side="left", padx=3)

    # === Movement Handlers ===
    def start_move(self, event):
        # Only move if clicking on frame, not buttons
        if event.widget in [self.main_frame, self.top_bar, self.status_label, self.status_dot]:
            self.x = event.x
            self.y = event.y

    def stop_move(self, event):
        self.x = None
        self.y = None

    def do_move(self, event):
        if hasattr(self, 'x') and self.x is not None:
            deltax = event.x - self.x
            deltay = event.y - self.y
            x = self.root.winfo_x() + deltax
            y = self.root.winfo_y() + deltay
            self.root.geometry(f"+{x}+{y}")

    # === Mode Toggle ===
    def _toggle_teach_mode(self):
        """Switch between Command and Teach mode"""
        self.feedback_mode = not self.feedback_mode
        
        if self.feedback_mode:
            # Teach Mode Active
            self.entry.configure(placeholder_text="💡 Teach me: What should I improve?")
            self.entry.focus_set()
            self.btn_teach.configure(
                fg_color=("#ffaa00", "#ff8800"),
                hover_color=("#ff8800", "#ff6600")
            )
            self.btn_action.configure(
                text="💾",
                fg_color=("#ffaa00", "#ff8800"),
                hover_color=("#ff8800", "#ff6600")
            )
            self.status_label.configure(text="Teach Mode")
            self.status_dot.configure(text_color="#ffaa00")
        else:
            # Command Mode
            self.entry.configure(placeholder_text="What would you like me to do?")
            self.btn_teach.configure(
                fg_color="#2a2a2a",
                hover_color="#3d3d3d"
            )
            self.btn_action.configure(
                text="▶",
                fg_color=("#0066ff", "#0052cc"),
                hover_color=("#0052cc", "#0041a3")
            )
            self.status_label.configure(text="Ready")
            self.status_dot.configure(text_color="#00ff88")

    # === Input Handlers ===
    def _on_enter(self, event=None):
        self._on_submit()
    
    def _on_escape(self, event=None):
        self.root.withdraw()  # Hide
    
    def _on_submit(self):
        command = self.entry.get().strip()
        
        # Stop if running
        if self.is_running and not self.feedback_mode:
            self.on_command("STOP_IMMEDIATELY")
            self.is_running = False
            self.btn_action.configure(
                text="⏹",
                fg_color="#cc0000",
                hover_color="#990000"
            )
            self.status_label.configure(text="Stopping...")
            self.status_dot.configure(text_color="#ff3333")
            # Auto-switch to Teach Mode
            self.root.after(1500, self._activate_correction_mode)
            return

        if not command:
            return
            
        self.entry.delete(0, 'end')
        
        # Feedback Mode
        if self.feedback_mode:
            msg = f"FEEDBACK: {command}"
            self.on_command(msg)
            self._toggle_teach_mode()  # Reset
            self.set_status("Feedback Saved! 🧠", "#ffaa00")
            
        # Command Mode
        else:
            self.is_running = True
            self.on_command(command)

    def _activate_correction_mode(self):
        """Auto-activate teach mode after stop"""
        if not self.feedback_mode:
            self._toggle_teach_mode()
            self.entry.configure(placeholder_text="🛑 I stopped. What went wrong?")
            self.entry.focus_set()

    # === Status Updates ===
    def set_status(self, text: str, color: str = ""):
        """Update UI status with animations"""
        
        if "Running" in text or "Executing" in text or "working" in text.lower():
            # Running State
            self.is_running = True
            self.btn_action.configure(
                text="⏹",
                fg_color=("#cc0000", "#990000"),
                hover_color=("#990000", "#770000")
            )
            self.status_label.configure(text="Working...")
            self.status_dot.configure(text_color="#3366ff")
            self.entry.configure(placeholder_text=f"🔄 {text}...")
            self._start_activity_animation()
            
        elif "Fail" in text or "Error" in text or "❌" in text:
            # Error State
            self.is_running = False
            self._stop_activity_animation()
            self.btn_action.configure(
                text="❌",
                fg_color="#cc0000"
            )
            self.status_label.configure(text="Failed")
            self.status_dot.configure(text_color="#ff3333")
            self.root.after(3000, self._reset_ui)
            
        elif "Complet" in text or "Success" in text or "✅" in text:
            # Success State
            self.is_running = False
            self._stop_activity_animation()
            self.btn_action.configure(
                text="✅",
                fg_color="#00cc44"
            )
            self.status_label.configure(text="Completed")
            self.status_dot.configure(text_color="#00ff88")
            self.root.after(3000, self._reset_ui)
            
        else:
            # Custom status
            self.status_label.configure(text=text)

    def _reset_ui(self):
        """Reset to idle state"""
        self.is_running = False
        self.btn_action.configure(
            text="▶",
            fg_color=("#0066ff", "#0052cc"),
            hover_color=("#0052cc", "#0041a3")
        )
        self.entry.configure(placeholder_text="What would you like me to do?")
        self.status_label.configure(text="Ready")
        self.status_dot.configure(text_color="#00ff88")
        self._stop_activity_animation()

    # === Activity Animation ===
    def _start_activity_animation(self):
        """Start animated activity indicator"""
        self.activity_animation = True
        self._animate_activity()
    
    def _stop_activity_animation(self):
        """Stop activity animation"""
        self.activity_animation = False
        self.activity_label.configure(text="")
    
    def _animate_activity(self):
        """Animate the activity indicator"""
        if not self.activity_animation:
            return
        
        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        current = getattr(self, '_activity_frame', 0)
        self.activity_label.configure(text=frames[current % len(frames)])
        self._activity_frame = current + 1
        
        self.root.after(80, self._animate_activity)

    # === Focus Management ===
    def focus(self):
        """Bring window to front and focus input"""
        self.root.deiconify()
        self.root.lift()
        self.entry.focus_set()
        
    def run(self):
        """Start UI main loop"""
        self.root.mainloop()

    def destroy(self):
        """Clean shutdown"""
        self._stop_activity_animation()
        self.root.quit()
        self.root.destroy()


class UIController:
    """Controls the UI and handles hotkeys"""
    
    def __init__(self, on_command: Callable[[str], None]):
        self.on_command = on_command
        self.ui: Optional[PremiumFloatingUI] = None
        config = get_config()
        self.activation_hotkey = config.ui.activation_hotkey
    
    def start(self):
        self.ui = PremiumFloatingUI(self.on_command)
        log.info(f"✨ Premium UI started (activate with {self.activation_hotkey})")
    
    def run(self):
        if self.ui:
            self.ui.run()
    
    def activate(self):
        if self.ui:
            self.ui.root.after(0, self.ui.focus)
    
    def set_status(self, text: str, color: str = "#00ff00"):
        if self.ui:
            self.ui.root.after(0, lambda: self.ui.set_status(text, color))
    
    def stop(self):
        if self.ui:
            self.ui.destroy()
