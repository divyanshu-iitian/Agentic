"""
Voice Cache Primer 🚀
Pre-generates common words and emotional tags for instant speech.
"""

import os
import sys
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from voice.voice_narrator import VoiceNarrator
from utils.logger import log

def prime_cache():
    narrator = VoiceNarrator()
    
    # 1. Essential Emotion Tags
    emotions = [
        "[laugh]", "[sigh]", "[pause]", "[uv_break]", "[clears throat]", "[thinking]"
    ]
    
    # 2. Common Conversational Words
    common_words = [
        "hello", "hi", "hey", "yes", "no", "okay", "done", "opening", "google", 
        "chrome", "youtube", "task", "finished", "working", "processing", 
        "sorry", "failed", "completed", "ready", "agent", "assistant"
    ]
    
    log.info(f"Priming cache with {len(emotions) + len(common_words)} tokens...")
    
    for token in emotions + common_words:
        # get_token_audio will automatically generate and save if missing
        log.info(f"Priming: {token}")
        narrator.cache_manager.get_token_audio(token)
        
    log.info("✅ Cache priming complete!")

if __name__ == "__main__":
    prime_cache()
