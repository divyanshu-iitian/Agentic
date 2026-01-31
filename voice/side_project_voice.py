"""
Side Project: Emotional Voice AI 🎭
Focused on: Tone, Non-verbal cues (laughs, sighs), and human-like interaction.
"""

import os
import sys
import time
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import log

class EmotionalAssistant:
    def __init__(self, engine_type="chattts"):
        self.engine_type = engine_type
        self.engine = None
        
        log.info(f"🎭 Emotional Assistant initializing with {engine_type}...")
        
        if engine_type == "chattts":
            try:
                from voice.human_voice import HumanVoiceEngine
                self.engine = HumanVoiceEngine()
            except ImportError:
                log.error("HumanVoiceEngine module not found")
                
    def interact(self, text: str, mode: str = "natural"):
        """
        Interacts with specific human-like behavioral cues.
        Modes: 'natural', 'excited', 'thoughtful', 'hesitant'
        """
        if not self.engine:
            return "Engine not ready"
            
        processed_text = text
        
        # Add behavioral cues based on mode
        if mode == "excited":
            processed_text = f"[laugh] Oh wow! {text}!! [uv_break]"
        elif mode == "thoughtful":
            processed_text = f"Hmm... [pause] let me think. [pause] {text}"
        elif mode == "hesitant":
            processed_text = f"[um] {text}... [pause] I think."
        elif mode == "natural":
            processed_text = f"{text} [uv_break]"
            
        log.info(f"🎭 Behavioral Mode: {mode}")
        audio_file = self.engine.generate(processed_text)
        
        if audio_file:
            self.engine.play(audio_file)
            return f"Played audio: {audio_file}"
        return "Failed to generate audio"

if __name__ == "__main__":
    # This will be tested once ChatTTS is installed
    print("Emotional Assistant Ready for integration.")
