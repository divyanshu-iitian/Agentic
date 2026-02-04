"""
Aether AI - Smart Voice Assistant Launcher 🚀
"""

from core.agent import Agent
from llm.ollama_client import OllamaClient
from ui.assistant_ui import AssistantUI
from utils.logger import log

def main():
    log.info("Starting Anudeshak Assistant...")
    
    # Initialize Engine (Agent handles its own LLM init)
    agent = Agent()
    
    # Initialize UI
    app = AssistantUI(agent)
    
    log.info("UI Ready! Click START TALKING or Type to begin.")
    app.mainloop()

if __name__ == "__main__":
    main()
