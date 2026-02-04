"""
Voice Narrator 🎙️
Refines Ollama outputs using Groq and narrates them via Bark (Sequentially).
"""

import os
import sys
import threading
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
        from voice.simple_voice import SimpleVoiceEngine
        from voice.voice_cache_manager import VoiceCacheManager
        self.bark = BarkVoiceEngine()
        self.fast_voice = SimpleVoiceEngine()
        self.cache_manager = VoiceCacheManager(voice_engine=self.bark)
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "llama-3.1-8b-instant" 
        self.lock = threading.Lock()
        log.info("Voice Narrator initialized (Instant Cache + Hybrid Mode)")

    def classify_intent(self, user_text: str) -> dict:
        """
        Classifies if the user wants a casual chat or a computer task.
        Returns: {"type": "CHAT"|"TASK", "task": "..."|None, "response": "..."|None}
        """
        try:
            prompt = f"""
            System: You are an AI Desktop Assistant. Classify the user's intent.
            - If it's a casual conversation/greeting/question, set type to 'CHAT' and provide a short, human-like response with emotional tags like [laugh] or [pause].
            - If it's a request to perform a task on the computer (open app, search, etc.), set type to 'TASK' and extract the specific task.
            
            User Input: "{user_text}"
            
            Return ONLY a JSON object:
            {{ "type": "CHAT" or "TASK", "task": "extracted task if TASK else null", "response": "human response if CHAT else null" }}
            """

            completion = self.groq_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3, # Low temp for classification
                response_format={ "type": "json_object" }
            )
            
            import json
            result = json.loads(completion.choices[0].message.content)
            log.info(f"Intent Analysis: {result}")
            return result
        except Exception as e:
            log.error(f"Intent classification failed: {e}")
            return {"type": "CHAT", "task": None, "response": "I'm sorry, I'm having trouble understanding."}

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
            log.info(f"Groq Refined: {refined_text}")
            return refined_text
        except Exception as e:
            log.error(f"Groq refinement failed: {e}")
            return raw_input # Fallback

    def say(self, raw_text: str, fast_mode: bool = False):
        """
        Narrates text dynamically.
        - If cached: Plays instantly in a sequence.
        - If not: Generates, caches, then plays.
        """
        if fast_mode:
            log.info(f"Anudeshak Fast Speak: {raw_text}")
            self.fast_voice.speak(raw_text)
            return

        with self.lock:
            # 1. Refine text with Groq (Anudeshak style)
            human_text = self.refine_response(raw_text)
            log.info(f"Anudeshak Refined: {human_text}")
            
            # 2. Assemble the entire response fluently
            try:
                full_audio = self.cache_manager.assemble_sentence(human_text)
                if full_audio is not None:
                    log.info("Anudeshak is speaking fluently...")
                    self.bark.play_direct(full_audio)
                else:
                    log.warning("No audio clips found/generated for the response.")
            except Exception as e:
                log.error(f"Anudeshak voice playback failed: {e}")

if __name__ == "__main__":
    # Test
    narrator = VoiceNarrator()
    narrator.say("Task completed successfully. Opened chrome browser.")
