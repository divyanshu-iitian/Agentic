import os
import re
import numpy as np
from pathlib import Path
from scipy.io.wavfile import read as read_wav, write as write_wav
from utils.logger import log

class VoiceCacheManager:
    def __init__(self, cache_dir="voice_cache", voice_engine=None):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.engine = voice_engine
        self.index = {}
        self.sample_rate = 24000 # Bark standard
        self.load_index()
        log.info("Voice Cache Manager (Scipy Optimized) initialized")

    def load_index(self):
        """Maps filenames to tokens."""
        for f in self.cache_dir.glob("*.wav"):
            token = f.stem.lower()
            self.index[token] = str(f)

    def trim_silence_np(self, audio_data, threshold=0.01):
        """Trims silence using numpy."""
        if len(audio_data) == 0: return audio_data
        mask = np.abs(audio_data) > threshold
        if not np.any(mask): return audio_data[:100] # return tiny bit of silence
        start = np.argmax(mask)
        end = len(audio_data) - np.argmax(mask[::-1])
        return audio_data[start:end]

    def get_token_audio(self, token):
        """Fetches audio array from cache or generates it if missing."""
        token_clean = token.lower().strip().replace(" ", "_")
        # Filter out characters that can't be filenames
        token_clean = re.sub(r'[^\w\s]', '', token_clean)
        
        if not token_clean:
            return None
        
        # Check cache
        if token_clean in self.index:
            path = self.index[token_clean]
            if os.path.exists(path):
                try:
                    sr, data = read_wav(path)
                    if data.dtype != np.float32:
                        data = data.astype(np.float32) / 32768.0
                    return data
                except Exception as e:
                    log.error(f"Error reading cache for {token_clean}: {e}")

        # Generate on-demand if missing
        if self.engine:
            log.info(f"Anudeshak generating new word: {token_clean}")
            try:
                # Generate single word audio
                audio_path = self.engine.generate(token, save_file=True)
                if audio_path and os.path.exists(audio_path):
                    sr, data = read_wav(audio_path)
                    data_clean = self.trim_silence_np(data)
                    
                    # Save to permanent cache
                    new_path = self.cache_dir / f"{token_clean}.wav"
                    write_wav(str(new_path.absolute()), sr, data_clean)
                    
                    self.index[token_clean] = str(new_path.absolute())
                    self.sample_rate = sr
                    
                    # Cleanup Bark's temporary file
                    if os.path.exists(audio_path): os.remove(audio_path)
                    
                    # Return normalized
                    if data_clean.dtype != np.float32:
                        return data_clean.astype(np.float32) / 32768.0
                    return data_clean
            except Exception as e:
                log.error(f"Failed to generate word '{token_clean}': {e}")
        return None

    def assemble_sentence(self, text):
        """Stitches audio arrays together into a single fluent response."""
        tokens = re.findall(r"\[.*?\]|\w+|[.,!?;]", text)
        clips = []
        
        log.info(f"Assembling response for: {text}")
        
        for token in tokens:
            if token in ".,!?;":
                # Add natural pause for punctuation
                clips.append(np.zeros(int(self.sample_rate * 0.3), dtype=np.float32))
                continue
                
            clip = self.get_token_audio(token)
            if clip is not None:
                clips.append(clip)
        
        if clips:
            # Concatenate all parts for a single fluent playback
            return np.concatenate(clips)
        return None
