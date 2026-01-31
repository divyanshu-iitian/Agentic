# Voice AI Module 🎙️

Complete human-like voice synthesis system with multiple TTS models.

## Features ✨

- **Multiple TTS Models**: XTTS, Bark, Piper, Custom Python
- **Voice Cloning**: Clone any voice from 5-second sample
- **Emotional Speech**: Happy, sad, angry tones
- **Non-verbal Sounds**: Laughs, sighs, music (Bark)
- **Speed Control**: Adjust speech rate
- **Multi-lingual**: English, Hindi, Spanish, and more
- **Real-time Capable**: Fast enough for interactive use

## Quick Start 🚀

### 1. Install Dependencies

```bash
# Core (required)
pip install TTS scipy numpy

# Optional models
pip install git+https://github.com/suno-ai/bark.git  # Bark
pip install piper-tts  # Piper
```

### 2. Test Installation

```bash
python test_voice.py
```

### 3. Basic Usage

```python
from voice import speak

# Simple speech
speak("Hello, I am your AI assistant!")

# With specific model
speak("This is XTTS", model="xtts")
speak("[laughs] This is Bark!", model="bark")
```

## Models Comparison 📊

| Model | Quality | Speed | Voice Clone | Emotions | Size |
|-------|---------|-------|-------------|----------|------|
| **XTTS v2** | ⭐⭐⭐⭐⭐ | ⚡⚡⚡⚡ | ✅ Yes | ❌ No | ~2GB |
| **Bark** | ⭐⭐⭐⭐⭐ | ⚡⚡⚡ | ❌ No | ✅ Yes | ~1GB |
| **Piper** | ⭐⭐⭐⭐ | ⚡⚡⚡⚡⚡ | ❌ No | ❌ No | ~50MB |
| **Custom** | ⭐⭐ | ⚡⚡⚡⚡⚡ | ❌ No | ❌ No | 0MB |

## Examples 💡

### Voice Cloning

```python
from voice import clone_voice

# Record your voice (5-10 seconds) and save as "my_voice.wav"
clone_voice("my_voice.wav", "This is my cloned voice!")
```

### Emotional Speech

```python
from voice import VoiceEngine

engine = VoiceEngine()

# Happy
engine.speak("Great news!", model="bark", emotion="happy")

# With sounds
engine.speak("[laughs] That's funny! [sighs]", model="bark")
```

### Integration with Agent

```python
from voice import VoiceEngine
from core.agent import Agent

class VoiceAgent:
    def __init__(self):
        self.agent = Agent()
        self.voice = VoiceEngine()
    
    def execute_with_voice(self, command: str):
        # Speak acknowledgment
        self.voice.speak(f"Executing: {command}", model="piper")
        
        # Execute task
        result = self.agent.execute_task(command)
        
        # Speak result
        if result.success:
            self.voice.speak("Done!", model="xtts")
        else:
            self.voice.speak("Failed", model="bark", emotion="sad")
```

## File Structure 📁

```
voice/
├── __init__.py           # Module exports
├── voice_engine.py       # Main engine (all models)
├── requirements_voice.txt # Dependencies
├── VOICE_TESTING.md      # Testing guide
└── README.md             # This file

voice_output/             # Generated audio files
├── xtts_*.wav
├── bark_*.wav
├── piper_*.wav
└── custom_*.wav
```

## Testing 🧪

### Run Test Suite

```bash
python test_voice.py
```

Options:
1. Basic Speech
2. All Models
3. Emotional Speech
4. Speed Control
5. Voice Cloning
6. Interactive Test
7. Run All Tests

### Manual Testing

```python
from voice import VoiceEngine

engine = VoiceEngine()

# Check available models
print(engine.list_models())

# Test each model
for model in engine.list_models():
    engine.speak("Test", model=model)
```

## Advanced Usage 🔧

### Custom Voice Assistant

```python
from voice import VoiceEngine
import speech_recognition as sr

class VoiceAssistant:
    def __init__(self):
        self.voice = VoiceEngine()
        self.recognizer = sr.Recognizer()
    
    def listen(self):
        with sr.Microphone() as source:
            audio = self.recognizer.listen(source)
        return self.recognizer.recognize_google(audio)
    
    def respond(self, text):
        self.voice.speak(text, model="xtts")
    
    def run(self):
        self.respond("Hello! How can I help?")
        while True:
            user_input = self.listen()
            # Process and respond
            self.respond(f"You said: {user_input}")
```

### Multi-lingual

```python
engine = VoiceEngine()

# English
engine.speak("Hello", model="xtts")

# Hindi
engine.speak("नमस्ते", model="xtts")

# Spanish
engine.speak("Hola", model="xtts")
```

## Troubleshooting 🔧

### Model Not Loading

```python
# Check available models
from voice import VoiceEngine
engine = VoiceEngine()
print(engine.list_models())

# Install missing models
# pip install TTS  # XTTS
# pip install git+https://github.com/suno-ai/bark.git  # Bark
```

### Audio Not Playing

```python
# Manual playback
import winsound
winsound.PlaySound("voice_output/output.wav", winsound.SND_FILENAME)
```

### Voice Cloning Failed

- Ensure reference audio is 5-10 seconds
- Use WAV format, 22050 Hz
- Clear speech, no background noise

## Performance Tips ⚡

1. **Preload models** at startup
2. **Use Piper** for quick responses
3. **Use XTTS** for quality
4. **Cache audio** for repeated phrases

## Roadmap 🗺️

- [ ] Real-time streaming TTS
- [ ] More emotion controls
- [ ] Custom voice training
- [ ] Speech-to-speech translation
- [ ] Noise reduction
- [ ] Voice effects (pitch, reverb)

## Credits 🙏

- **Coqui TTS**: https://github.com/coqui-ai/TTS
- **Bark**: https://github.com/suno-ai/bark
- **Piper**: https://github.com/rhasspy/piper

## License 📄

Same as main project (MIT)

---

**Your agent can now SPEAK!** 🗣️🚀
