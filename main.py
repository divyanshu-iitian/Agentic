"""Agentic desktop runtime entry point."""

import asyncio
import sys

import keyboard as kb
from dotenv import load_dotenv

from core.agent import Agent
from core.config import get_config
from ui.floating_input import UIController
from utils.logger import log

# Load environment variables from .env file
load_dotenv()


class AgenticApp:
    """Main application"""

    def __init__(self):
        self.agent = Agent()
        self.ui: UIController | None = None

        config = get_config()
        self.activation_hotkey = config.ui.activation_hotkey

    def on_command(self, command: str):
        """Handle command from UI"""
        log.info("Received command from desktop UI")

        # Handle Feedback
        if command.startswith("FEEDBACK:"):
            feedback = command.replace("FEEDBACK:", "").strip()
            self.agent.learn_from_feedback(feedback)
            return

        # Handle Stop
        if command == "STOP_IMMEDIATELY":
            log.warning("Stop command received from UI")
            self.agent.emergency_stop()
            return

        # Execute task in background thread
        import threading

        thread = threading.Thread(
            target=lambda: asyncio.run(self._execute_command(command)), daemon=True
        )
        thread.start()

    async def _execute_command(self, command: str):
        """Execute command in async context"""
        if self.ui is None:
            return
        self.ui.set_status("Running")

        success = await self.agent.execute_task(command)

        if success:
            self.ui.set_status("Completed")
        else:
            self.ui.set_status("Failed")

    def setup_hotkeys(self):
        """Setup global hotkeys"""
        # UI activation hotkey
        kb.add_hotkey(self.activation_hotkey, self.ui.activate)
        log.info(f"Hotkey registered: {self.activation_hotkey}")

    def run(self):
        """Run the application"""
        log.info("=" * 60)
        log.info("Agentic local runtime starting")
        log.info("=" * 60)

        # Check Ollama connection
        if not self.agent.llm.check_health():
            log.error("Ollama server not reachable")
            log.error("Please start Ollama first:")
            log.error("  1. Install from https://ollama.ai")
            log.error("  2. Run: ollama serve")
            log.error(f"  3. Pull a model: ollama pull {self.agent.llm.model}")
            sys.exit(1)

        log.info("Ollama connection OK")

        # List available models
        models = self.agent.llm.list_models()
        if models:
            log.info(f"Available models: {', '.join(models)}")

        # Start agent
        self.agent.start()

        # Start UI
        self.ui = UIController(on_command=self.on_command)
        self.ui.start()

        # Setup hotkeys
        self.setup_hotkeys()

        log.info("=" * 60)
        log.info("Agent is ready")
        log.info(f"Press {self.activation_hotkey} to activate")
        log.info("Press Ctrl+Alt+Q to emergency stop")
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
        if self.agent.browser_executor.browser is not None:
            asyncio.run(self.agent.browser_executor.cleanup())
        log.info("Shutdown complete")


def main():
    """Main entry point"""
    app = AgenticApp()
    app.run()


if __name__ == "__main__":
    main()
