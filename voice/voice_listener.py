"""
Voice Listener - STT (Speech to Text) Module 🎤
Converts user's spoken words into text.
"""

import speech_recognition as sr
from utils.logger import log

class VoiceListener:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        # Adjust for ambient noise on init
        with self.microphone as source:
            log.info("🎤 Adjusting for ambient noise... Please wait.")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
        log.info("✅ Voice Listener ready")

    def listen(self):
        """Listens for a single phrase and returns the text."""
        with self.microphone as source:
            log.info("👂 Listening...")
            try:
                # Phrasal threshold and timeout to keep it snappy
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                log.info("☁️ Recognizing...")
                text = self.recognizer.recognize_google(audio)
                log.info(f"🗣️ User said: {text}")
                return text
            except sr.WaitTimeoutError:
                log.warning("⌛ Listening timed out")
                return None
            except sr.UnknownValueError:
                log.warning("❓ Could not understand audio")
                return None
            except sr.RequestError as e:
                log.error(f"❌ STT Service error: {e}")
                return None
            except Exception as e:
                log.error(f"❌ Voice listening error: {e}")
                return None

if __name__ == "__main__":
    listener = VoiceListener()
    while True:
        t = listener.listen()
        if t:
            print(f"Recognized: {t}")
