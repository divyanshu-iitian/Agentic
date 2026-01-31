"""
Voice Narrator 🎙️
Refines Ollama outputs using Groq and narrates them via Bark (Sequentially).
"""

import os
import sys
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from groq import Groq
from voice.bark_engine import BarkVoiceEngine
from utils.logger import log
from dotenv import load_dotenv

load_dotenv()

class VoiceNarrator:
    def __init__(self):
        self.bark = BarkVoiceEngine()
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        # Using Llama 3 70B for better conversational output than prompt-guard
        self.model = "llama3-70b-8192" 
        log.info("🎙️ Voice Narrator initialized with Groq + Bark")

    def refine_response(self, raw_input: str) -> str:
        """Refines the raw terminal/agent output into human speech using Groq."""
        try:
            prompt = f"""
            You are a helpful, human-like AI desktop assistant. 
            Convert the following technical status into a very short, natural, conversational response.
            Add vocal cues like [laugh], [sigh], or [pause] where appropriate to sound human.
            
            Technical Status: {raw_input}
            
            Conversational Response:"""

            completion = self.groq_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=60, # Keep it short for voice
                top_p=1,
                stream=False
            )
            
            refined_text = completion.choices[0].message.content.strip()
            log.info(f"🤖 Groq Refined: {refined_text}")
            return refined_text
        except Exception as e:
            log.error(f"Groq refinement failed: {e}")
            return raw_input # Fallback

    def say(self, raw_text: str):
        """Sequentially refines and speaks the text."""
        # 1. Refine with Groq
        human_text = self.refine_response(raw_text)
        
        # 2. Generate with Bark
        audio_file = self.bark.generate(human_text)
        
        # 3. Play (Synchronous - will wait until finished on Windows)
        if audio_file:
            log.info(f"🔊 Narrating: {human_text}")
            self.bark.play(audio_file)

if __name__ == "__main__":
    # Test
    narrator = VoiceNarrator()
    narrator.say("Task completed successfully. Opened chrome browser.")
