import os
import sys
from pathlib import Path
from voice.voice_narrator import VoiceNarrator
from dotenv import load_dotenv

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

def test_narrator_refinement():
    # We mock Bark initialization to save time
    from voice.bark_engine import BarkVoiceEngine
    original_init = BarkVoiceEngine.__init__
    BarkVoiceEngine.__init__ = lambda self: None
    BarkVoiceEngine.is_loaded = True
    
    narrator = VoiceNarrator()
    test_inputs = [
        "Task completed successfully. Opened chrome browser.",
        "Error: Start menu not found.",
        "Navigating to youtube.com"
    ]
    
    for inp in test_inputs:
        print(f"\n--- Raw: {inp} ---")
        refined = narrator.refine_response(inp)
        print(f"Refined: {refined}")

if __name__ == "__main__":
    test_narrator_refinement()
