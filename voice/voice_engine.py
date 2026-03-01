"""
Voice AI Module - Human-like Speech Synthesis 🎙️

This module integrates multiple open-source TTS models:
1. Coqui XTTS v2 - Best quality, voice cloning
2. Bark - Expressive, emotional, non-verbal sounds
3. Piper - Ultra-fast, lightweight
4. Custom Python-based simple TTS

Usage:
    from voice.voice_engine import VoiceEngine
    
    engine = VoiceEngine()
    engine.speak("Hello, I am your AI assistant", model="xtts")
"""

import os
import sys
import time
import numpy as np
from pathlib import Path
from typing import Optional, Literal
from utils.logger import log

# Create voice output directory
VOICE_DIR = Path("voice_output")
VOICE_DIR.mkdir(exist_ok=True)


class VoiceEngine:
    """
    Unified interface for multiple TTS models.
    Supports: XTTS, Bark, Piper, and custom Python TTS.
    """
    
    def __init__(self):
        self.models_loaded = {}
        self.default_model = "piper"  # Fastest for real-time
        
        log.info("🎙️ Voice Engine initializing...")
        
        # Try to load models (lazy loading)
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Check which TTS libraries are available"""
        self.available_models = []
        
        # Check Coqui TTS (XTTS)
        try:
            import TTS
            self.available_models.append("xtts")
            log.info("✅ Coqui XTTS available")
        except ImportError:
            log.warning("⚠️  Coqui TTS not installed (pip install TTS)")
        
        # Check Bark
        try:
            import bark
            self.available_models.append("bark")
            log.info("✅ Bark available")
        except ImportError:
            log.warning("⚠️  Bark not installed (pip install git+https://github.com/suno-ai/bark.git)")
        
        # Check Piper
        try:
            import subprocess
            result = subprocess.run(["piper", "--version"], capture_output=True)
            if result.returncode == 0:
                self.available_models.append("piper")
                log.info("✅ Piper available")
        except FileNotFoundError:
            log.warning("⚠️  Piper not installed (pip install piper-tts)")
        
        # Custom Python TTS always available
        self.available_models.append("custom")
        log.info("✅ Custom Python TTS available")
        
        if not self.available_models:
            log.error("❌ No TTS models available!")
        else:
            log.info(f"🎙️ Available models: {', '.join(self.available_models)}")
    
    def speak(
        self,
        text: str,
        model: Literal["xtts", "bark", "piper", "custom", "auto"] = "auto",
        voice: Optional[str] = None,
        emotion: Optional[str] = None,
        speed: float = 1.0,
        play: bool = True
    ) -> str:
        """
        Generate speech from text.
        
        Args:
            text: Text to speak
            model: TTS model to use ("xtts", "bark", "piper", "custom", "auto")
            voice: Voice file for cloning (XTTS only)
            emotion: Emotion tag (Bark only: "happy", "sad", "angry")
            speed: Speech speed multiplier
            play: Whether to play audio immediately
        
        Returns:
            Path to generated audio file
        """
        # Auto-select best available model
        if model == "auto":
            if "xtts" in self.available_models:
                model = "xtts"
            elif "piper" in self.available_models:
                model = "piper"
            elif "bark" in self.available_models:
                model = "bark"
            else:
                model = "custom"
        
        # Check if model is available
        if model not in self.available_models:
            log.warning(f"Model {model} not available, falling back to custom")
            model = "custom"
        
        log.info(f"🎙️ Generating speech with {model}: '{text[:50]}...'")
        
        # Route to appropriate model
        if model == "xtts":
            output_file = self._speak_xtts(text, voice, speed)
        elif model == "bark":
            output_file = self._speak_bark(text, emotion)
        elif model == "piper":
            output_file = self._speak_piper(text, speed)
        else:
            output_file = self._speak_custom(text, speed)
        
        # Play audio if requested
        if play and output_file:
            self._play_audio(output_file)
        
        return output_file
    
    def _speak_xtts(self, text: str, voice: Optional[str], speed: float) -> str:
        """Generate speech using Coqui XTTS v2"""
        try:
            from TTS.api import TTS
            
            # Load model if not already loaded
            if "xtts" not in self.models_loaded:
                log.info("Loading XTTS model...")
                self.models_loaded["xtts"] = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
            
            tts = self.models_loaded["xtts"]
            output_file = str(VOICE_DIR / f"xtts_{int(time.time())}.wav")
            
            # Generate speech
            if voice and os.path.exists(voice):
                # Voice cloning
                tts.tts_to_file(
                    text=text,
                    file_path=output_file,
                    speaker_wav=voice,
                    language="en"
                )
            else:
                # Default voice
                tts.tts_to_file(
                    text=text,
                    file_path=output_file,
                    language="en"
                )
            
            log.info(f"✅ XTTS generated: {output_file}")
            return output_file
            
        except Exception as e:
            log.error(f"XTTS failed: {e}")
            return self._speak_custom(text, speed)
    
    def _speak_bark(self, text: str, emotion: Optional[str]) -> str:
        """Generate speech using Bark (expressive TTS)"""
        try:
            import torch
            
            # Fix PyTorch 2.6 weights_only issue with Bark models
            if "bark" not in self.models_loaded:
                _original_torch_load = torch.load
                def _patched_torch_load(*args, **kwargs):
                    if 'weights_only' not in kwargs:
                        kwargs['weights_only'] = False
                    return _original_torch_load(*args, **kwargs)
                torch.load = _patched_torch_load
            
            from bark import SAMPLE_RATE, generate_audio, preload_models
            from scipy.io.wavfile import write as write_wav
            
            # Load models if not already loaded
            if "bark" not in self.models_loaded:
                log.info("Loading Bark models...")
                preload_models()
                self.models_loaded["bark"] = True
            
            # Add emotion tags
            if emotion:
                text = f"[{emotion}] {text}"
            
            # Generate audio
            audio_array = generate_audio(text)
            
            # Save to file
            output_file = str(VOICE_DIR / f"bark_{int(time.time())}.wav")
            write_wav(output_file, SAMPLE_RATE, audio_array)
            
            log.info(f"✅ Bark generated: {output_file}")
            return output_file
            
        except Exception as e:
            log.error(f"Bark failed: {e}")
            return self._speak_custom(text, 1.0)
    
    def _speak_piper(self, text: str, speed: float) -> str:
        """Generate speech using Piper (fast TTS)"""
        try:
            import subprocess
            
            output_file = str(VOICE_DIR / f"piper_{int(time.time())}.wav")
            
            # Use default Piper model
            # Note: User needs to download a model first
            model_path = "en_US-lessac-medium.onnx"
            
            # Check if model exists
            if not os.path.exists(model_path):
                log.warning("Piper model not found, using custom TTS")
                return self._speak_custom(text, speed)
            
            # Run Piper
            process = subprocess.run(
                ["piper", "--model", model_path, "--output_file", output_file],
                input=text.encode(),
                capture_output=True
            )
            
            if process.returncode == 0:
                log.info(f"✅ Piper generated: {output_file}")
                return output_file
            else:
                raise Exception(f"Piper failed: {process.stderr.decode()}")
                
        except Exception as e:
            log.error(f"Piper failed: {e}")
            return self._speak_custom(text, speed)
    
    def _speak_custom(self, text: str, speed: float) -> str:
        """
        Custom Python-based TTS (fallback).
        Uses simple sine wave synthesis for demonstration.
        """
        try:
            import wave
            
            log.info("Using custom Python TTS (basic)")
            
            # Simple text-to-beep mapping (placeholder)
            # In a real implementation, you'd use phoneme synthesis
            
            sample_rate = 22050
            duration = len(text) * 0.1 / speed  # Rough estimate
            
            # Generate simple tone (placeholder for actual TTS)
            t = np.linspace(0, duration, int(sample_rate * duration))
            frequency = 440  # A4 note
            audio = np.sin(2 * np.pi * frequency * t)
            
            # Add some variation based on text
            for i, char in enumerate(text):
                freq_offset = (ord(char) % 10) * 50
                segment_start = int(i * len(audio) / len(text))
                segment_end = int((i + 1) * len(audio) / len(text))
                audio[segment_start:segment_end] *= np.sin(
                    2 * np.pi * (frequency + freq_offset) * t[segment_start:segment_end]
                )
            
            # Normalize
            audio = (audio * 32767).astype(np.int16)
            
            # Save to WAV
            output_file = str(VOICE_DIR / f"custom_{int(time.time())}.wav")
            with wave.open(output_file, 'w') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio.tobytes())
            
            log.info(f"✅ Custom TTS generated: {output_file}")
            log.warning("⚠️  Custom TTS is basic - install proper TTS for better quality")
            
            return output_file
            
        except Exception as e:
            log.error(f"Custom TTS failed: {e}")
            return None
    
    def _play_audio(self, file_path: str):
        """Play audio file"""
        try:
            if sys.platform == "win32":
                import winsound
                winsound.PlaySound(file_path, winsound.SND_FILENAME)
            elif sys.platform == "darwin":
                os.system(f"afplay {file_path}")
            else:
                os.system(f"aplay {file_path}")
            
            log.info(f"🔊 Played: {file_path}")
            
        except Exception as e:
            log.error(f"Failed to play audio: {e}")
    
    def clone_voice(self, reference_audio: str, text: str) -> str:
        """
        Clone a voice from reference audio.
        Only works with XTTS model.
        
        Args:
            reference_audio: Path to 5-10 second audio sample
            text: Text to speak in cloned voice
        
        Returns:
            Path to generated audio file
        """
        if "xtts" not in self.available_models:
            log.error("Voice cloning requires XTTS model")
            return None
        
        log.info(f"🎭 Cloning voice from: {reference_audio}")
        return self._speak_xtts(text, reference_audio, 1.0)
    
    def list_models(self) -> list:
        """List available TTS models"""
        return self.available_models
    
    def set_default_model(self, model: str):
        """Set default TTS model"""
        if model in self.available_models:
            self.default_model = model
            log.info(f"Default model set to: {model}")
        else:
            log.error(f"Model {model} not available")


# Convenience functions
def speak(text: str, **kwargs):
    """Quick speak function"""
    engine = VoiceEngine()
    return engine.speak(text, **kwargs)


def clone_voice(reference: str, text: str):
    """Quick voice cloning function"""
    engine = VoiceEngine()
    return engine.clone_voice(reference, text)


if __name__ == "__main__":
    # Test the voice engine
    print("🎙️ Testing Voice Engine...")
    
    engine = VoiceEngine()
    
    print(f"\nAvailable models: {engine.list_models()}")
    
    # Test each available model
    test_text = "Hello, I am your AI assistant. I can speak in multiple voices!"
    
    for model in engine.list_models():
        print(f"\n🎙️ Testing {model}...")
        try:
            output = engine.speak(test_text, model=model, play=False)
            print(f"✅ Generated: {output}")
        except Exception as e:
            print(f"❌ Failed: {e}")
    
    print("\n✅ Voice Engine test complete!")
