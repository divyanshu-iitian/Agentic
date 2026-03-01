"""
Agentic — Local AI Desktop & Browser Automation Agent

Main entry point.
"""

import asyncio
import sys
import keyboard as kb
from dotenv import load_dotenv
from core.agent import Agent
from core.config import get_config
from ui.floating_input import UIController
from ui.camera_ui import get_camera_ui
from utils.logger import log

# Load environment variables from .env file
load_dotenv()


class AgenticApp:
    """Main application"""
    
    def __init__(self):
        self.agent = Agent()
        self.ui: UIController = None
        
        config = get_config()
        self.activation_hotkey = config.ui.activation_hotkey
    
    def on_command(self, command: str):
        """Handle command from UI"""
        print(f"DEBUG: Main Received -> {command}")
        log.info(f"📨 Received command: {command}")
        
        # Handle Feedback
        if command.startswith("FEEDBACK:"):
            feedback = command.replace("FEEDBACK:", "").strip()
            print(f"DEBUG: Processing Feedback -> {feedback}")
            self.agent.learn_from_feedback(feedback)
            return
            
        # Handle Stop
        if command == "STOP_IMMEDIATELY":
            log.warning("🛑 STOP command received from UI")
            self.agent.emergency_stop()
            # We don't need to join the thread, it should exit gracefully
            return
        
        # Execute task in background thread
        import threading
        thread = threading.Thread(
            target=lambda: asyncio.run(self._execute_command(command)),
            daemon=True
        )
        thread.start()
    
    async def _execute_command(self, command: str):
        """Execute command in async context"""
        self.ui.set_status("Running...", "#ffff00")
        
        success = await self.agent.execute_task(command)
        
        if success:
            self.ui.set_status("✅ Completed", "#00ff00")
        else:
            self.ui.set_status("❌ Failed", "#ff0000")
    
    def setup_hotkeys(self):
        """Setup global hotkeys"""
        # UI activation hotkey
        kb.add_hotkey(self.activation_hotkey, self.ui.activate)
        log.info(f"Hotkey registered: {self.activation_hotkey}")
    
    def run(self):
        """Run the application"""
        log.info("=" * 60)
        log.info("🚀 AGENTIC — Local AI Agent Starting")
        log.info("=" * 60)
        
        # Check Ollama connection
        if not self.agent.llm.check_health():
            log.error("❌ Ollama server not reachable!")
            log.error("Please start Ollama first:")
            log.error("  1. Install from https://ollama.ai")
            log.error("  2. Run: ollama serve")
            log.error("  3. Pull a model: ollama pull qwen2.5:7b")
            sys.exit(1)
        
        log.info("✅ Ollama connection OK")
        
        # List available models
        models = self.agent.llm.list_models()
        if models:
            log.info(f"Available models: {', '.join(models)}")
        
        # Start agent
        self.agent.start()
        
        # Camera UI - optional (can be enabled later)
        # Disabled for now to avoid threading issues
        # try:
        #     camera_ui = get_camera_ui()
        #     camera_ui.start()
        #     log.info("✨ Camera UI started")
        # except Exception as e:
        #     log.warning(f"Failed to start camera UI: {e}")
        
        # Start UI
        self.ui = UIController(on_command=self.on_command)
        self.ui.start()
        
        # Setup hotkeys
        self.setup_hotkeys()
        
        log.info("=" * 60)
        log.info("✨ Agent is READY")
        log.info(f"Press {self.activation_hotkey} to activate")
        log.info(f"Press Ctrl+Alt+Q to emergency stop")
        log.info("=" * 60)
        
        # Run UI mainloop (blocks on main thread)
        try:
            self.ui.run()
        except KeyboardInterrupt:
            log.info("Shutdown requested")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Cleanup resources"""
        log.info("Cleaning up...")
        self.agent.stop()
        asyncio.run(self.agent.browser_executor.cleanup())
        log.info("Goodbye! 👋")


def main():
    """Main entry point"""
    app = AgenticApp()
    app.run()


if __name__ == "__main__":
    main()
