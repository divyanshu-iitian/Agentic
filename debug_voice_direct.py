import os
import sys
import torch
import numpy as np
import sounddevice as sd
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from bark import SAMPLE_RATE, generate_audio, preload_models
from utils.logger import log

# 🛠️ Monkeypatch for PyTorch 2.6+
original_load = torch.load
def patched_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return original_load(*args, **kwargs)
torch.load = patched_load

def test_direct_audio():
    log.info("🎙️ Starting Audio Direct Test...")
    
    # 1. Preload
    log.info("Loading Bark models (this might take a moment)...")
    preload_models()
    
    # 2. Generate a very short clip
    text = "Hello! [laugh] Audio test successful."
    log.info(f"Generating: {text}")
    
    # Generate
    audio_array = generate_audio(text, history_prompt="v2/en_speaker_6")
    
    # 3. Play Direct
    log.info("🔊 Attempting to play directly to speakers...")
    try:
        sd.play(audio_array, SAMPLE_RATE)
        sd.wait()
        log.info("✅ Finished playback!")
    except Exception as e:
        log.error(f"❌ Playback failed: {e}")

if __name__ == "__main__":
    test_direct_audio()
