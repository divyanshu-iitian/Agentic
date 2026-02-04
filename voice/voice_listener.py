"""
Voice Listener 2.0 - Groq Whisper Edition 🎤
Uses sounddevice for recording and Groq's API for ultra-fast STT.
"""

import os
import time
import queue
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write as write_wav
from groq import Groq
from utils.logger import log
from dotenv import load_dotenv

load_dotenv()

class VoiceListener:
    def __init__(self, sample_rate=16000):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.sample_rate = sample_rate
        self.is_recording = False
        log.info("✅ Groq Whisper Voice Listener ready")

    def record_until_silence(self, duration=5):
        """Records for a fixed duration for now (simplest for test)."""
        log.info(f"👂 Recording for {duration} seconds...")
        recording = sd.rec(int(duration * self.sample_rate), samplerate=self.sample_rate, channels=1)
        sd.wait()
        return recording

    def transcribe(self, recording):
        """Sends audio to Groq Whisper."""
        temp_file = "temp_voice.wav"
        try:
            # Save temporary file
            write_wav(temp_file, self.sample_rate, recording)
            
            # Transcribe via Groq
            with open(temp_file, "rb") as file:
                transcription = self.client.audio.transcriptions.create(
                    file=(temp_file, file.read()),
                    model="whisper-large-v3-turbo",
                    response_format="text",
                )
            
            # Cleanup
            if os.path.exists(temp_file):
                os.remove(temp_file)
                
            log.info(f"🗣️ Transcribed: {transcription}")
            return transcription
        except Exception as e:
            log.error(f"❌ Transcription failed: {e}")
            return None

if __name__ == "__main__":
    listener = VoiceListener()
    rec = listener.record_until_silence(3)
    print(listener.transcribe(rec))
