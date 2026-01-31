# Voice AI Testing & Examples 🎙️

## Quick Start

### 1. Install Dependencies

```bash
# Core TTS library (Coqui XTTS)
pip install TTS

# Bark (Expressive TTS)
pip install git+https://github.com/suno-ai/bark.git

# Piper (Fast TTS)
pip install piper-tts

# Audio processing
pip install scipy numpy
```

### 2. Download Piper Model (Optional)

```bash
# Download a voice model
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
```

---

## Usage Examples

### Example 1: Basic Speech

```python
from voice import speak

# Simple speech (auto-selects best model)
speak("Hello, I am your AI assistant!")

# Specify model
speak("This is XTTS speaking", model="xtts")
speak("This is Bark speaking", model="bark")
speak("This is Piper speaking", model="piper")
```

### Example 2: Voice Cloning

```python
from voice import clone_voice

# Record 5-10 seconds of your voice and save as "my_voice.wav"

# Clone your voice!
clone_voice(
    reference="my_voice.wav",
    text="Hello, this is me speaking through AI!"
)
```

### Example 3: Emotional Speech (Bark)

```python
from voice import VoiceEngine

engine = VoiceEngine()

# Happy
engine.speak("I'm so excited!", model="bark", emotion="happy")

# Sad
engine.speak("I'm sorry about that", model="bark", emotion="sad")

# With non-verbal sounds
engine.speak("[laughs] That's hilarious! [sighs]", model="bark")
```

### Example 4: Speed Control

```python
from voice import speak

# Normal speed
speak("This is normal speed", speed=1.0)

# Fast
speak("This is fast", speed=1.5)

# Slow
speak("This is slow", speed=0.7)
```

### Example 5: Integration with Agent

```python
from voice import VoiceEngine
from core.agent import Agent

class VoiceAgent:
    def __init__(self):
        self.agent = Agent()
        self.voice = VoiceEngine()
    
    def execute_with_voice(self, command: str):
        # Acknowledge command
        self.voice.speak(f"Executing: {command}", model="piper")
        
        # Execute
        result = self.agent.execute_task(command)
        
        # Report result
        if result.success:
            self.voice.speak("Task completed successfully!", model="xtts")
        else:
            self.voice.speak(f"Task failed: {result.error}", model="bark", emotion="sad")

# Usage
voice_agent = VoiceAgent()
voice_agent.execute_with_voice("Open Chrome and go to YouTube")
```

---

## Testing

### Test All Models

```bash
cd "c:\Users\user\Desktop\The Biggest Project"
python voice/voice_engine.py
```

### Test Individual Model

```python
from voice import VoiceEngine

engine = VoiceEngine()

# Check available models
print(engine.list_models())

# Test specific model
engine.speak("Testing XTTS", model="xtts", play=True)
```

---

## Advanced Usage

### Custom Voice Assistant

```python
from voice import VoiceEngine
import speech_recognition as sr

class VoiceAssistant:
    def __init__(self):
        self.voice = VoiceEngine()
        self.recognizer = sr.Recognizer()
    
    def listen(self):
        """Listen to user input"""
        with sr.Microphone() as source:
            print("🎤 Listening...")
            audio = self.recognizer.listen(source)
        
        try:
            text = self.recognizer.recognize_google(audio)
            print(f"You said: {text}")
            return text
        except:
            return None
    
    def respond(self, text: str):
        """Speak response"""
        self.voice.speak(text, model="xtts")
    
    def conversation_loop(self):
        """Interactive conversation"""
        self.respond("Hello! I'm your voice assistant. How can I help?")
        
        while True:
            user_input = self.listen()
            
            if user_input:
                if "goodbye" in user_input.lower():
                    self.respond("Goodbye! Have a great day!")
                    break
                
                # Process command (integrate with your agent)
                response = f"You said: {user_input}"
                self.respond(response)

# Usage
assistant = VoiceAssistant()
assistant.conversation_loop()
```

### Multi-lingual Support

```python
from voice import VoiceEngine

engine = VoiceEngine()

# English
engine.speak("Hello, how are you?", model="xtts")

# Hindi (if XTTS supports)
engine.speak("नमस्ते, आप कैसे हैं?", model="xtts")

# Spanish
engine.speak("Hola, ¿cómo estás?", model="xtts")
```

---

## Model Comparison

### Quality Test

```python
from voice import VoiceEngine

engine = VoiceEngine()

test_text = "The quick brown fox jumps over the lazy dog"

# Test each model
for model in ["xtts", "bark", "piper", "custom"]:
    print(f"\n🎙️ Testing {model}...")
    output = engine.speak(test_text, model=model, play=False)
    print(f"Output: {output}")
```

### Speed Benchmark

```python
import time
from voice import VoiceEngine

engine = VoiceEngine()

text = "This is a speed test"

for model in engine.list_models():
    start = time.time()
    engine.speak(text, model=model, play=False)
    elapsed = time.time() - start
    print(f"{model}: {elapsed:.2f}s")
```

---

## Troubleshooting

### Model Not Available

```python
from voice import VoiceEngine

engine = VoiceEngine()

# Check what's available
print("Available models:", engine.list_models())

# Install missing models
# pip install TTS  # for XTTS
# pip install git+https://github.com/suno-ai/bark.git  # for Bark
# pip install piper-tts  # for Piper
```

### Audio Not Playing

```python
# Manual playback
import winsound

winsound.PlaySound("voice_output/xtts_123456.wav", winsound.SND_FILENAME)
```

### Voice Cloning Not Working

```python
# Ensure reference audio is:
# - 5-10 seconds long
# - Clear speech
# - WAV format
# - 22050 Hz sample rate

from voice import clone_voice

# Convert to proper format if needed
# Use Audacity or ffmpeg

clone_voice("reference.wav", "Test cloning")
```

---

## Performance Tips

### 1. Preload Models

```python
from voice import VoiceEngine

# Load models at startup
engine = VoiceEngine()
engine.speak("Initializing...", model="xtts", play=False)  # Loads model
engine.speak("Initializing...", model="bark", play=False)  # Loads model

# Now subsequent calls are faster
```

### 2. Use Appropriate Model

```python
# For quick responses: Piper
engine.speak("Quick response", model="piper")

# For quality: XTTS
engine.speak("Important announcement", model="xtts")

# For expressiveness: Bark
engine.speak("[excited] Great news!", model="bark")
```

### 3. Cache Audio

```python
# Generate once, play multiple times
output = engine.speak("Welcome message", model="xtts", play=False)

# Play cached audio
engine._play_audio(output)
engine._play_audio(output)  # Instant!
```

---

## Integration with Desktop Agent

### Add Voice to Agent

```python
# In core/agent.py

from voice import VoiceEngine

class Agent:
    def __init__(self):
        # ... existing code ...
        self.voice = VoiceEngine()
        self.voice_enabled = True
    
    def execute_task(self, task: str):
        # Acknowledge
        if self.voice_enabled:
            self.voice.speak(f"Starting task: {task}", model="piper")
        
        # Execute
        result = self._execute(task)
        
        # Report
        if self.voice_enabled:
            if result.success:
                self.voice.speak("Task complete!", model="xtts")
            else:
                self.voice.speak("Task failed", model="bark", emotion="sad")
        
        return result
```

---

## Next Steps

1. ✅ Test basic functionality: `python voice/voice_engine.py`
2. ✅ Try voice cloning with your own voice
3. ✅ Integrate with desktop agent
4. ✅ Add speech recognition for full voice control
5. ✅ Experiment with emotions and tones

**Your agent can now SPEAK!** 🗣️🚀
