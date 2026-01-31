"""
Aether AI - Voice Assistant Application Glue 🚀
Integrates UI, STT, Groq Intent, and Bark TTS.
"""

import webview
import threading
import os
import json
import asyncio
from voice.voice_listener import VoiceListener
from voice.voice_narrator import VoiceNarrator
from utils.logger import log

class AssistantAPI:
    def __init__(self, window, agent):
        self.window = window
        self.agent = agent
        self.listener = VoiceListener()
        self.narrator = VoiceNarrator()
        log.info("🚀 Assistant API initialized")

    def listen_and_process(self):
        """Called from JS when Mic is clicked."""
        # 1. Start listening
        text = self.listener.listen()
        if not text:
            return None
        
        # 2. Show user message in UI
        self.window.evaluate_js(f"addMessage('{text.replace("'", "\\'")}', true)")
        
        # 3. Process Intent with Groq
        intent = self.narrator.classify_intent(text)
        
        if intent["type"] == "CHAT":
            # Just talk back
            response = intent["response"]
            self.window.evaluate_js(f"addMessage('{response.replace("'", "\\'")}', false)")
            self.narrator.say(response) # Bark speaks
            
        elif intent["type"] == "TASK":
            # Task execution!
            task = intent["task"]
            self.window.evaluate_js(f"addMessage('Starting task: {task}', false)")
            
            # Start agent in a separate thread to not block UI
            def run_agent():
                # We need to run the async agent loop
                asyncio.run(self.agent.run(task))
                # When done, notify UI
                self.window.evaluate_js("addMessage('Task completed! [laugh]', false)")
            
            threading.Thread(target=run_agent).start()
            
        return text

def start_voice_assistant(agent):
    # Load the HTML file
    html_path = os.path.abspath("ui/voice_ui.html")
    
    # Create webview window
    # transparent=True for glassmorphism effect on Windows
    window = webview.create_window(
        'Aether AI', 
        f'file://{html_path}', 
        width=420, 
        height=620, 
        transparent=True, 
        frameless=True,
        on_top=True
    )
    
    api = AssistantAPI(window, agent)
    window.expose(api.listen_and_process)
    
    webview.start(debug=True)

if __name__ == "__main__":
    # Test stub
    from core.agent import Agent
    from llm.ollama_client import OllamaClient
    
    # Initialize basic agent for testing
    llm = OllamaClient()
    agent = Agent(llm)
    
    start_voice_assistant(agent)
