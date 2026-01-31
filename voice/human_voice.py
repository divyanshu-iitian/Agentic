"""
Human-Like Voice Module (ChatTTS) 🎙️

This module uses ChatTTS which is specifically designed for conversational scenarios.
It supports:
- Natural pauses: [pause]
- Laughter: [laugh]
- Oral fillers: [um], [uh]
- Emotion control
"""

import os
import sys
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import torch
import torchaudio
import numpy as np
from utils.logger import log

# Create voice output directory
VOICE_DIR = Path("voice_output/human")
VOICE_DIR.mkdir(parents=True, exist_ok=True)

class HumanVoiceEngine:
    def __init__(self):
        self.chat = None
        self.is_loaded = False
        log.info("🎙️ Initializing Human Voice Engine (ChatTTS)...")
        
        try:
            import ChatTTS
            self.chat = ChatTTS.Chat()
            # Loading models (this might download files on first run)
            self.chat.load_models()
            self.is_loaded = True
            log.info("✅ ChatTTS models loaded successfully")
        except ImportError:
            log.error("❌ ChatTTS not installed. Run: pip install ChatTTS")
        except Exception as e:
            log.error(f"❌ Failed to load ChatTTS: {e}")

    def generate(self, text: str, voice_seed: int = 42, refine_text: bool = True):
        """
        Generate natural human speech.
        
        Args:
            text: Input text (can include tags like [laugh], [pause])
            voice_seed: Seed for voice characteristics
            refine_text: Automatically add oral fillers and pauses
        """
        if not self.is_loaded:
            log.error("Engine not loaded")
            return None

        log.info(f"🎤 Generating human voice for: {text}")
        
        try:
            # 1. Refine text if requested (adds [uv_break], [laugh] based on context)
            if refine_text:
                # Add a bit of randomness/humanity
                params_refine_text = {
                    'prompt': '[oral_2][laugh_0][break_4]'
                }
                # chat.infer returns a list of audio arrays
                wavs = self.chat.infer([text], params_refine_text=params_refine_text)
            else:
                wavs = self.chat.infer([text])

            # 2. Save output
            output_path = VOICE_DIR / f"speech_{int(torch.randint(0, 10000, (1,)))}.wav"
            
            # Save using torchaudio
            # ChatTTS returns numpy array, convert to torch tensor
            audio_tensor = torch.from_numpy(wavs[0])
            if audio_tensor.ndim == 1:
                audio_tensor = audio_tensor.unsqueeze(0)
                
            torchaudio.save(str(output_path), audio_tensor, 24000)
            log.info(f"✅ Audio saved to {output_path}")
            return str(output_path)

        except Exception as e:
            log.error(f"❌ Generation failed: {e}")
            return None

    def play(self, file_path: str):
        """Play audio on Windows"""
        if not file_path or not os.path.exists(file_path):
            return
            
        import winsound
        winsound.PlaySound(file_path, winsound.SND_FILENAME)

if __name__ == "__main__":
    # Test script
    engine = HumanVoiceEngine()
    if engine.is_loaded:
        test_text = "Hello! [laugh] I am your new AI assistant. [pause] I sound much more human now, don't you think?"
        audio_file = engine.generate(test_text)
        if audio_file:
            print(f"Playing generated audio: {audio_file}")
            engine.play(audio_file)
