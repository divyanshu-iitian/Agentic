"""
Floating Input Box UI (Premium Redesign)

Modern, GPU-accelerated interface using CustomTkinter.
Inspired by Spotlight/Raycast.
"""

import customtkinter as ctk
import tkinter as tk
from typing import Callable, Optional
from core.config import get_config
from utils.logger import log

# Set default theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class FloatingInputBox:
    """Persistent floating UI for agent control (Premium Version)"""
    
    def __init__(self, on_command: Callable[[str], None]):
        """Initialize premium UI"""
        self.on_command = on_command
        config = get_config()
        
        # Main Window
        self.root = ctk.CTk()
        self.root.title("Agentic AI")
        
        # 🎨 Premium Window Settings
        self.root.overrideredirect(True)  # Remove standard window chrome (No Title Bar)
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.96)  # Slight transparency (Glass effect)
        
        # Geometry (Centered Top)
        width = 700
        height = 80
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = int(screen_height * 0.15) # 15% from top
        
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.configure(fg_color="#1a1a1a") # Dark background
        self.root.eval('tk::PlaceWindow . center') # Try to center
        
        # Make draggable
        self.root.bind("<ButtonPress-1>", self.start_move)
        self.root.bind("<ButtonRelease-1>", self.stop_move)
        self.root.bind("<B1-Motion>", self.do_move)
        
        # Build UI
        self._build_ui()
        
        # Focus handling
        self.root.after(100, self.focus)
        
        log.info("💎 Premium UI initialized")

    def _build_ui(self):
        """Build modern UI components"""
        # Outer Frame (Border/Glow effect placeholder)
        self.frame = ctk.CTkFrame(
            self.root, 
            fg_color="#2b2b2b", 
            corner_radius=15,
            border_width=1,
            border_color="#404040"
        )
        self.frame.pack(fill="both", expand=True, padx=2, pady=2)
        
        # 🤖 Icon/Label
        self.lbl_icon = ctk.CTkLabel(
            self.frame, 
            text="🤖", 
            font=("Segoe UI Emoji", 24)
        )
        self.lbl_icon.pack(side="left", padx=(15, 5), pady=10)
        
        # 📝 Main Input
        self.entry = ctk.CTkEntry(
            self.frame,
            placeholder_text="Ask Agentic to do something...",
            font=("Segoe UI", 14),
            height=45,
            fg_color="#1a1a1a",
            text_color="#ffffff",
            border_width=0,
            corner_radius=10
        )
        self.entry.pack(side="left", fill="both", expand=True, padx=5, pady=15)
        self.entry.bind("<Return>", self._on_enter)
        self.entry.bind("<Escape>", self._on_escape)
        
        
        # 🧠 Teach Button
        self.btn_teach = ctk.CTkButton(
            self.frame,
            text="🧠",
            width=35,
            height=35,
            font=("Segoe UI Emoji", 14),
            fg_color="#333333",
            hover_color="#4d4d4d",
            corner_radius=8,
            command=self._toggle_teach_mode
        )
        self.btn_teach.pack(side="right", padx=(0, 5), pady=10)
        
        # ▶️ Action Button
        self.btn_action = ctk.CTkButton(
            self.frame,
            text="RUN",
            width=60,
            height=35,
            font=("Segoe UI", 11, "bold"),
            fg_color="#0066cc",
            hover_color="#0052a3",
            corner_radius=8,
            command=self._on_submit
        )
        self.btn_action.pack(side="right", padx=(5, 5), pady=10)
        
        self.feedback_mode = False
        self.is_running = False

    def _toggle_teach_mode(self):
        """Switch between Command and Teach mode"""
        self.feedback_mode = not self.feedback_mode
        
        if self.feedback_mode:
            self.entry.configure(placeholder_text="Tell me: What did I do right/wrong?")
            self.entry.focus_set()
            self.btn_teach.configure(fg_color="#e6b800") # Active yellow
            self.btn_action.configure(text="SAVE", fg_color="#e6b800", hover_color="#ccda00")
        else:
            self.entry.configure(placeholder_text="Ask Agentic to do something...")
            self.btn_teach.configure(fg_color="#333333")
            self.btn_action.configure(text="RUN", fg_color="#0066cc", hover_color="#0052a3")

        
    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def stop_move(self, event):
        self.x = None
        self.y = None

    def do_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")

    def _on_enter(self, event=None):
        self._on_submit()
    
    def _on_escape(self, event=None):
        self.root.withdraw() # Hide
    
    def _on_submit(self):
        command = self.entry.get().strip()
        
        # Priority 1: Stop if running
        if self.is_running and not self.feedback_mode:
            self.on_command("STOP_IMMEDIATELY")
            self.is_running = False
            self.btn_action.configure(text="STOPPING...", fg_color="#990000")
            # Auto-switch to Teach Mode for immediate correction
            self.root.after(1000, self._activate_correction_mode)
            return

        if not command: return
        self.entry.delete(0, 'end')
        
        # Priority 2: Feedback
        if self.feedback_mode:
            msg = f"FEEDBACK: {command}"
            print(f"DEBUG: UI Sending -> {msg}")
            self.on_command(msg)
            self._toggle_teach_mode() # Reset
            self.set_status("Feedback Saved! 🧠", "#e6b800")
            
        # Priority 3: Run new command
        else:
            self.is_running = True
            self.on_command(command)
            # Button updates to STOP via set_status call from Agent

    def _activate_correction_mode(self):
        """Automatically ask for feedback after stop"""
        if not self.feedback_mode:
            self._toggle_teach_mode()
            self.entry.configure(placeholder_text="I stopped. What did I do wrong? (Correction)")
            self.entry.focus_set()

    def set_status(self, text: str, color: str = ""):
        """Update UI to reflect state"""
        if "Running" in text or "Executing" in text:
            self.is_running = True
            self.btn_action.configure(text="STOP", fg_color="#cc0000", hover_color="#990000") # Red STOP
            self.entry.configure(placeholder_text=f"Agent is working: {text}...")
            
        elif "Fail" in text or "Error" in text or "Stopped" in text:
            self.is_running = False
            self.btn_action.configure(text="❌", fg_color="#cc0000")
            # We let correction mode handle the input reset if needed
            
        elif "Complet" in text or "Success" in text:
            self.is_running = False
            self.btn_action.configure(text="✅", fg_color="#00cc44")
            self.root.after(3000, self._reset_ui)
        else:
            self._reset_ui()
            
    def _reset_ui(self):
        """Reset to idle state"""
        self.is_running = False
        self.btn_action.configure(text="RUN", fg_color="#0066cc", hover_color="#0052a3")
        self.entry.configure(placeholder_text="Ask Agentic to do something...")
            
    def focus(self):
        self.root.deiconify()
        self.root.lift()
        self.entry.focus_set()
        
    def run(self):
        self.root.mainloop()

    def destroy(self):
        self.root.quit()
        self.root.destroy()


class UIController:
    """Controls the UI and handles hotkeys"""
    
    def __init__(self, on_command: Callable[[str], None]):
        self.on_command = on_command
        self.ui: Optional[FloatingInputBox] = None
        config = get_config()
        self.activation_hotkey = config.ui.activation_hotkey
    
    def start(self):
        self.ui = FloatingInputBox(self.on_command)
        log.info(f"UI started (activate with {self.activation_hotkey})")
    
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
