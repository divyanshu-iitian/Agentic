"""
Voice Cache Manager & Assembler 💎
Provides instant human-like speech by stitching pre-generated audio clips.
"""

import os
import sys

# 🛠️ Python 3.13+ Compatibility Hack
# audioop was removed in 3.13, pydub needs it.
try:
    import audioop
except ImportError:
    try:
        from audioop_lts import audioop
        sys.modules['audioop'] = audioop
    except ImportError:
        pass

import re
import numpy as np
from pathlib import Path
from pydub import AudioSegment
from utils.logger import log

class VoiceCacheManager:
    def __init__(self, cache_dir="voice_cache", voice_engine=None):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.engine = voice_engine
        self.index = {}
        self.load_index()
        log.info("Voice Cache Manager initialized")

    def load_index(self):
        """Maps filenames to tokens."""
        for f in self.cache_dir.glob("*.wav"):
            token = f.stem.lower()
            self.index[token] = str(f)

    def get_token_audio(self, token):
        """Fetches audio from cache or generates it if missing."""
        token_clean = token.lower().strip()
        if token_clean in self.index:
            return AudioSegment.from_wav(self.index[token_clean])
        
        # If it's a critical emotion tag or common word, generate and save it
        if self.engine and (token.startswith("[") or len(token) > 0):
            log.info(f"Generating new cache token: {token}")
            # Use bark to generate a single token audio
            # Note: Single tokens generate very fast
            audio_path = self.engine.generate(token, save_file=True)
            if audio_path:
                # Move to cache
                new_path = self.cache_dir / f"{token_clean}.wav"
                if os.path.exists(new_path): os.remove(new_path)
                os.rename(audio_path, new_path)
                self.index[token_clean] = str(new_path)
                return AudioSegment.from_wav(str(new_path))
        return None

    def assemble_sentence(self, text):
        """Stitches audio clips together for a full sentence."""
        # Split by words and [tags]
        tokens = re.findall(r"\[.*?\]|\w+|[.,!?;]", text)
        log.info(f"Assembling tokens: {tokens}")
        
        full_audio = None
        
        for token in tokens:
            audio_clip = self.get_token_audio(token)
            if audio_clip:
                if full_audio is None:
                    full_audio = audio_clip
                else:
                    # Apply small cross-fade for smooth transitions
                    full_audio = full_audio.append(audio_clip, crossfade=50)
            else:
                # Add a small silence for punctuation if missing
                if token in ".,!?;":
                    silence = AudioSegment.silent(duration=300)
                    if full_audio: full_audio += silence
        
        if full_audio:
            output_path = "voice_output/assembled_speech.wav"
            full_audio.export(output_path, format="wav")
            return output_path
        return None

if __name__ == "__main__":
    # Test logic
    # (Requires bark engine passed to constructor to generate missing tokens)
    pass
