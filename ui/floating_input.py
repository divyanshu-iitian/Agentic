"""
Floating Input Box UI

Always-on-top Tkinter interface for agent control.
"""

import tkinter as tk
from tkinter import ttk
import asyncio
import threading
from typing import Callable, Optional
from core.config import get_config
from utils.logger import log


class FloatingInputBox:
    """Persistent floating UI for agent commands"""
    
    def __init__(self, on_command: Callable[[str], None]):
        """
        Initialize floating input box.
        
        Args:
            on_command: Callback function when command is entered
        """
        self.on_command = on_command
        config = get_config()
        
        # Create window
        self.root = tk.Tk()
        self.root.title("Agentic AI")
        
        # Configure window
        self.root.attributes('-topmost', config.ui.always_on_top)
        self.root.geometry(f"{config.ui.window_width}x{config.ui.window_height}")
        
        # Style
        self.root.configure(bg="#1e1e1e")
        
        # Build UI
        self._build_ui(config)
        
        # Hotkey activation (handled separately in main)
        self.activation_hotkey = config.ui.activation_hotkey
        
        log.info("UI initialized")
    
    def _build_ui(self, config):
        """Build the UI components"""
        # Main frame
        main_frame = tk.Frame(self.root, bg="#1e1e1e")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Label
        label = tk.Label(
            main_frame,
            text="🤖 Agentic AI — Type your command:",
            bg="#1e1e1e",
            fg="#ffffff",
            font=("Segoe UI", 10)
        )
        label.pack(anchor=tk.W, pady=(0, 5))
        
        # Input frame
        input_frame = tk.Frame(main_frame, bg="#1e1e1e")
        input_frame.pack(fill=tk.X)
        
        # Text entry
        self.entry = tk.Entry(
            input_frame,
            bg="#2d2d2d",
            fg="#ffffff",
            font=("Segoe UI", config.ui.font_size),
            insertbackground="#ffffff",
            relief=tk.FLAT,
            highlightthickness=2,
            highlightbackground="#007acc",
            highlightcolor="#007acc"
        )
        self.entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=2)
        self.entry.bind("<Return>", self._on_enter)
        self.entry.bind("<Escape>", self._on_escape)
        
        # Submit button
        self.submit_btn = tk.Button(
            input_frame,
            text="Execute",
            bg="#007acc",
            fg="#ffffff",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            cursor="hand2",
            command=self._on_submit
        )
        self.submit_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Status label
        self.status_label = tk.Label(
            main_frame,
            text="Ready",
            bg="#1e1e1e",
            fg="#00ff00",
            font=("Segoe UI", 9)
        )
        self.status_label.pack(anchor=tk.W, pady=(5, 0))
    
    def _on_enter(self, event=None):
        """Handle Enter key press"""
        self._on_submit()
    
    def _on_escape(self, event=None):
        """Handle Escape key press"""
        self.entry.delete(0, tk.END)
        self.root.withdraw()
    
    def _on_submit(self):
        """Handle command submission"""
        command = self.entry.get().strip()
        
        if not command:
            return
        
        # Clear entry
        self.entry.delete(0, tk.END)
        
        # Update status
        self.set_status("Executing...", "#ffff00")
        
        # Call callback
        self.on_command(command)
    
    def set_status(self, text: str, color: str = "#00ff00"):
        """Update status label safely"""
        def _update():
            self.status_label.config(text=text, fg=color)
        
        self.root.after(0, _update)
    
    def focus(self):
        """Bring window to focus"""
        self.root.deiconify()
        self.root.lift()
        self.entry.focus_set()
    
    def run(self):
        """Start the UI main loop"""
        log.info("UI running")
        self.root.mainloop()
    
    def destroy(self):
        """Close the window"""
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
        """Start UI on main thread"""
        self.ui = FloatingInputBox(self.on_command)
        log.info(f"UI started (activate with {self.activation_hotkey})")
    
    def run(self):
        """Run UI mainloop (blocks)"""
        if self.ui:
            self.ui.run()
    
    def activate(self):
        """Activate UI (bring to focus)"""
        if self.ui:
            self.ui.root.after(0, self.ui.focus)
    
    def set_status(self, text: str, color: str = "#00ff00"):
        """Update status"""
        if self.ui:
            self.ui.root.after(0, lambda: self.ui.set_status(text, color))
    
    def stop(self):
        """Stop UI"""
        if self.ui:
            self.ui.destroy()
