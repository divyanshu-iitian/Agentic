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
log.info("Monkeypatched torch.load for Bark compatibility")

from bark import SAMPLE_RATE, generate_audio, preload_models
from scipy.io.wavfile import write as write_wav

class BarkVoiceEngine:
    def __init__(self):
        log.info("🎙️ Initializing Bark Voice Engine (Small Mode for Speed)...")
        
        # 🧹 Cleanup old files
        output_dir = Path("voice_output/bark")
        if output_dir.exists():
            for f in output_dir.glob("*.wav"):
                try:
                    os.remove(f)
                except:
                    pass
            log.info("🧹 Cleaned up old voice files")

        # Preload SMALL models for CPU speed
        preload_models(
            text_use_small=True,
            coarse_use_small=True,
            fine_use_small=True
        )
        self.is_loaded = True
        log.info("✅ Bark Small models preloaded")

    def generate(self, text: str, voice_preset: str = "v2/en_speaker_6", save_file: bool = True):
        """
        Generate human-like audio with Bark.
        
        Args:
            text: Text with tags like [laugh], [sigh], [music]
            voice_preset: Which speaker to use
            save_file: Whether to save to a disk file
        """
        log.info(f"🎤 Bark Generating: {text}")
        audio_array = generate_audio(text, history_prompt=voice_preset)
        
        if not save_file:
            return audio_array
            
        output_dir = Path("voice_output/bark")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        import time
        output_path = output_dir / f"bark_{int(time.time())}.wav"
        write_wav(str(output_path), SAMPLE_RATE, audio_array)
        
        log.info(f"✅ Bark audio saved to {output_path}")
        return str(output_path)

    def play_direct(self, audio_array):
        """Play audio directly from memory without saving to disk."""
        try:
            import sounddevice as sd
            log.info("🔊 Playing audio directly from memory...")
            sd.play(audio_array, SAMPLE_RATE)
            sd.wait() # Wait until finished
            log.info("✅ Finished playback")
        except Exception as e:
            log.error(f"❌ Direct playback failed: {e}")

    def play(self, file_path: str, delete_after: bool = False):
        """Play audio from file and optionally delete it."""
        if file_path and os.path.exists(file_path):
            import winsound
            log.info(f"🔊 Playing audio file: {file_path}")
            winsound.PlaySound(file_path, winsound.SND_FILENAME)
            
            if delete_after:
                try:
                    os.remove(file_path)
                    log.info(f"🧹 Deleted temporary audio file: {file_path}")
                except Exception as e:
                    log.warning(f"⚠️ Could not delete file {file_path}: {e}")

if __name__ == "__main__":
    engine = BarkVoiceEngine()
    test_text = "Hello! [laugh] This is a direct playback test. [pause] No files were permanently harmed."
    # Direct way
    audio_data = engine.generate(test_text, save_file=False)
    engine.play_direct(audio_data)
