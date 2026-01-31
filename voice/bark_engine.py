"""
Bark Voice Engine - Emotional & Human-like 🎙️
Supports: [laugh], [sigh], [music], [clears throat]
"""

import torch
import numpy as np
import os
import sys
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.logger import log

# 🛠️ THE ULTIMATE FIX: Monkeypatch torch.load
original_load = torch.load
def patched_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return original_load(*args, **kwargs)
torch.load = patched_load
log.info("🐒 Monkeypatched torch.load for Bark compatibility")

from bark import SAMPLE_RATE, generate_audio, preload_models
from scipy.io.wavfile import write as write_wav

class BarkVoiceEngine:
    def __init__(self):
        log.info("🎙️ Initializing Bark Voice Engine...")
        # Preload models
        preload_models()
        self.is_loaded = True
        log.info("✅ Bark models preloaded")

    def generate(self, text: str, voice_preset: str = "v2/en_speaker_6"):
        """
        Generate human-like audio with Bark.
        
        Args:
            text: Text with tags like [laugh], [sigh], [music]
            voice_preset: Which speaker to use
        """
        log.info(f"🎤 Bark Generating: {text}")
        audio_array = generate_audio(text, history_prompt=voice_preset)
        
        output_dir = Path("voice_output/bark")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        import time
        output_path = output_dir / f"bark_{int(time.time())}.wav"
        write_wav(str(output_path), SAMPLE_RATE, audio_array)
        
        log.info(f"✅ Bark audio saved to {output_path}")
        return str(output_path)

    def play(self, file_path: str):
        if file_path and os.path.exists(file_path):
            import winsound
            winsound.PlaySound(file_path, winsound.SND_FILENAME)

if __name__ == "__main__":
    engine = BarkVoiceEngine()
    test_text = "Hello! [laugh] This is Bark. [sigh] I can sound very human-like. [music]"
    audio = engine.generate(test_text)
    engine.play(audio)
