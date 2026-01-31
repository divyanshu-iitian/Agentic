"""
System Tray Integration

Adds a system tray icon with:
- Quick access menu
- Status notifications
- Settings
"""

import pystray
from PIL import Image, ImageDraw
import threading
from typing import Callable, Optional
from utils.logger import log


class SystemTrayIcon:
    """System tray icon for agent"""
    
    def __init__(self, on_activate: Callable, on_exit: Callable):
        self.on_activate = on_activate
        self.on_exit = on_exit
        self.icon: Optional[pystray.Icon] = None
        self.status = "Ready"
        
    def create_icon_image(self, color="#0066ff"):
        """Create a simple icon image"""
        # Create a 64x64 image
        width = 64
        height = 64
        image = Image.new('RGB', (width, height), color='black')
        draw = ImageDraw.Draw(image)
        
        # Draw a robot emoji-style icon
        # Head
        draw.ellipse([12, 12, 52, 52], fill=color, outline='white', width=2)
        
        # Eyes
        draw.ellipse([20, 24, 28, 32], fill='white')
        draw.ellipse([36, 24, 44, 32], fill='white')
        
        # Mouth
        draw.arc([22, 34, 42, 44], start=0, end=180, fill='white', width=2)
        
        return image
    
    def create_menu(self):
        """Create system tray menu"""
        return pystray.Menu(
            pystray.MenuItem(
                f"Status: {self.status}",
                lambda: None,
                enabled=False
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "🤖 Activate Agent",
                lambda: self.on_activate(),
                default=True
            ),
            pystray.MenuItem(
                "📊 View Logs",
                lambda: self._open_logs()
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "❌ Exit",
                lambda: self.on_exit()
            )
        )
    
    def _open_logs(self):
        """Open logs folder"""
        import subprocess
        import os
        logs_path = os.path.join(os.getcwd(), "logs")
        if os.path.exists(logs_path):
            subprocess.Popen(f'explorer "{logs_path}"')
    
    def start(self):
        """Start system tray icon"""
        def run_icon():
            image = self.create_icon_image()
            self.icon = pystray.Icon(
                "Agentic AI",
                image,
                "Agentic AI - Ready",
                menu=self.create_menu()
            )
            self.icon.run()
        
        thread = threading.Thread(target=run_icon, daemon=True)
        thread.start()
        log.info("🔔 System tray icon started")
    
    def update_status(self, status: str):
        """Update status in tray"""
        self.status = status
        if self.icon:
            self.icon.menu = self.create_menu()
            
            # Change icon color based on status
            if "Running" in status or "Working" in status:
                color = "#3366ff"  # Blue
            elif "Error" in status or "Failed" in status:
                color = "#ff3333"  # Red
            elif "Completed" in status or "Success" in status:
                color = "#00ff88"  # Green
            else:
                color = "#0066ff"  # Default blue
            
            self.icon.icon = self.create_icon_image(color)
            self.icon.title = f"Agentic AI - {status}"
    
    def notify(self, title: str, message: str):
        """Show notification"""
        if self.icon:
            self.icon.notify(message, title)
    
    def stop(self):
        """Stop tray icon"""
        if self.icon:
            self.icon.stop()
