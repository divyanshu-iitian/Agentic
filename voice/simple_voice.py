"""
Simple Voice Engine - Python 3.14 Compatible 🎙️

Since TTS libraries don't support Python 3.14 yet, this is a simplified
implementation using pyttsx3 (cross-platform, offline TTS).
"""

import os
import sys
from pathlib import Path
from typing import Optional, Literal

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from utils.logger import log
except ImportError:
    # Fallback logging
    class SimpleLogger:
        def info(self, msg): print(f"INFO: {msg}")
        def warning(self, msg): print(f"WARNING: {msg}")
        def error(self, msg): print(f"ERROR: {msg}")
    log = SimpleLogger()

# Create voice output directory
VOICE_DIR = Path("voice_output")
VOICE_DIR.mkdir(exist_ok=True)


class SimpleVoiceEngine:
    """
    Simple TTS engine using pyttsx3 (works on Python 3.14).
    """
    
    def __init__(self):
        self.engine = None
        self.available = False
        
        log.info("🎙️ Simple Voice Engine initializing...")
        
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            self.available = True
            
            # Configure voice
            voices = self.engine.getProperty('voices')
            if voices:
                # Try to use a better voice if available
                for voice in voices:
                    if 'david' in voice.name.lower() or 'zira' in voice.name.lower():
                        self.engine.setProperty('voice', voice.id)
                        break
            
            # Set properties
            self.engine.setProperty('rate', 150)  # Speed
            self.engine.setProperty('volume', 0.9)  # Volume
            
            log.info("✅ pyttsx3 TTS available")
            
        except ImportError:
            log.warning("⚠️  pyttsx3 not installed")
            log.info("   Install: pip install pyttsx3")
        except Exception as e:
            log.error(f"Failed to initialize TTS: {e}")
    
    def speak(
        self,
        text: str,
        rate: int = 150,
        volume: float = 0.9,
        save_to_file: Optional[str] = None
    ) -> bool:
        """
        Speak text using system TTS.
        
        Args:
            text: Text to speak
            rate: Speech rate (words per minute, default 150)
            volume: Volume (0.0 to 1.0, default 0.9)
            save_to_file: Optional path to save audio file
        
        Returns:
            True if successful, False otherwise
        """
        if not self.available:
            log.error("TTS not available")
            return False
        
        try:
            # Set properties
            self.engine.setProperty('rate', rate)
            self.engine.setProperty('volume', volume)
            
            log.info(f"🎙️ Speaking: '{text[:50]}...'")
            
            # Save to file if requested
            if save_to_file:
                self.engine.save_to_file(text, save_to_file)
                self.engine.runAndWait()
                log.info(f"💾 Saved to: {save_to_file}")
            else:
                # Speak directly
                self.engine.say(text)
                self.engine.runAndWait()
            
            return True
            
        except Exception as e:
            log.error(f"Speech failed: {e}")
            return False
    
    def list_voices(self):
        """List available system voices"""
        if not self.available:
            return []
        
        voices = self.engine.getProperty('voices')
        voice_list = []
        
        for voice in voices:
            voice_list.append({
                'id': voice.id,
                'name': voice.name,
                'languages': voice.languages
            })
        
        return voice_list
    
    def set_voice(self, voice_id: str):
        """Set voice by ID"""
        if not self.available:
            return False
        
        try:
            self.engine.setProperty('voice', voice_id)
            return True
        except:
            return False


# Convenience function
def speak(text: str, **kwargs):
    """Quick speak function"""
    engine = SimpleVoiceEngine()
    return engine.speak(text, **kwargs)


if __name__ == "__main__":
    # Test
    print("🎙️ Testing Simple Voice Engine...")
    
    engine = SimpleVoiceEngine()
    
    if engine.available:
        print("\n✅ TTS Available!")
        
        # List voices
        print("\nAvailable voices:")
        for i, voice in enumerate(engine.list_voices(), 1):
            print(f"{i}. {voice['name']}")
        
        # Test speech
        print("\n🎤 Testing speech...")
        engine.speak("Hello, I am your AI assistant. I can speak!")
        
        # Test different speeds
        print("\n⚡ Testing speeds...")
        engine.speak("This is slow speech", rate=100)
        engine.speak("This is normal speech", rate=150)
        engine.speak("This is fast speech", rate=200)
        
        print("\n✅ Test complete!")
    else:
        print("\n❌ TTS not available")
        print("Install: pip install pyttsx3")
