"""
Quick Voice AI Test Script 🎙️

Tests all available TTS models and demonstrates features.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voice.voice_engine import VoiceEngine
from utils.logger import log


def test_basic_speech():
    """Test basic text-to-speech"""
    print("\n" + "="*60)
    print("🎙️ TEST 1: Basic Speech")
    print("="*60)
    
    engine = VoiceEngine()
    
    test_phrases = [
        "Hello, I am your AI assistant.",
        "I can speak in multiple voices!",
        "This is a test of the voice engine."
    ]
    
    for phrase in test_phrases:
        print(f"\n📝 Speaking: '{phrase}'")
        try:
            output = engine.speak(phrase, play=False)
            print(f"✅ Generated: {output}")
        except Exception as e:
            print(f"❌ Error: {e}")


def test_all_models():
    """Test each available model"""
    print("\n" + "="*60)
    print("🎙️ TEST 2: All Models")
    print("="*60)
    
    engine = VoiceEngine()
    
    print(f"\n📋 Available models: {', '.join(engine.list_models())}")
    
    test_text = "Testing voice model"
    
    for model in engine.list_models():
        print(f"\n🎤 Testing {model.upper()}...")
        try:
            output = engine.speak(test_text, model=model, play=False)
            print(f"✅ {model}: {output}")
        except Exception as e:
            print(f"❌ {model} failed: {e}")


def test_emotions():
    """Test emotional speech (Bark only)"""
    print("\n" + "="*60)
    print("🎙️ TEST 3: Emotional Speech")
    print("="*60)
    
    engine = VoiceEngine()
    
    if "bark" not in engine.list_models():
        print("⚠️  Bark not available - skipping emotion test")
        print("   Install: pip install git+https://github.com/suno-ai/bark.git")
        return
    
    emotions = {
        "happy": "I'm so excited to help you!",
        "sad": "I'm sorry, I couldn't complete that task.",
        None: "[laughs] That's hilarious! [sighs]"
    }
    
    for emotion, text in emotions.items():
        print(f"\n😊 Emotion: {emotion or 'neutral + sounds'}")
        print(f"📝 Text: '{text}'")
        try:
            output = engine.speak(text, model="bark", emotion=emotion, play=False)
            print(f"✅ Generated: {output}")
        except Exception as e:
            print(f"❌ Error: {e}")


def test_speed_control():
    """Test speech speed control"""
    print("\n" + "="*60)
    print("🎙️ TEST 4: Speed Control")
    print("="*60)
    
    engine = VoiceEngine()
    
    text = "This is a speed test"
    speeds = [0.7, 1.0, 1.5]
    
    for speed in speeds:
        print(f"\n⚡ Speed: {speed}x")
        try:
            output = engine.speak(text, speed=speed, play=False)
            print(f"✅ Generated: {output}")
        except Exception as e:
            print(f"❌ Error: {e}")


def test_voice_cloning():
    """Test voice cloning (XTTS only)"""
    print("\n" + "="*60)
    print("🎙️ TEST 5: Voice Cloning")
    print("="*60)
    
    engine = VoiceEngine()
    
    if "xtts" not in engine.list_models():
        print("⚠️  XTTS not available - skipping voice cloning test")
        print("   Install: pip install TTS")
        return
    
    # Check for reference audio
    reference_files = [
        "my_voice.wav",
        "reference.wav",
        "voice_sample.wav"
    ]
    
    reference = None
    for ref_file in reference_files:
        if os.path.exists(ref_file):
            reference = ref_file
            break
    
    if not reference:
        print("⚠️  No reference audio found")
        print("   Create a 5-10 second recording and save as 'my_voice.wav'")
        print("   Then run this test again!")
        return
    
    print(f"\n🎭 Cloning voice from: {reference}")
    text = "Hello, this is my cloned voice speaking!"
    
    try:
        output = engine.clone_voice(reference, text)
        print(f"✅ Cloned voice: {output}")
    except Exception as e:
        print(f"❌ Error: {e}")


def interactive_test():
    """Interactive voice test"""
    print("\n" + "="*60)
    print("🎙️ INTERACTIVE TEST")
    print("="*60)
    
    engine = VoiceEngine()
    
    print(f"\nAvailable models: {', '.join(engine.list_models())}")
    print("\nType text to speak (or 'quit' to exit)")
    
    while True:
        text = input("\n📝 Enter text: ").strip()
        
        if text.lower() in ['quit', 'exit', 'q']:
            print("👋 Goodbye!")
            break
        
        if not text:
            continue
        
        # Ask for model
        model = input(f"🎤 Model ({'/'.join(engine.list_models())}) [auto]: ").strip() or "auto"
        
        try:
            print("🎙️ Generating speech...")
            output = engine.speak(text, model=model, play=True)
            print(f"✅ Played: {output}")
        except Exception as e:
            print(f"❌ Error: {e}")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🎙️ VOICE AI ENGINE - TEST SUITE")
    print("="*60)
    
    tests = [
        ("Basic Speech", test_basic_speech),
        ("All Models", test_all_models),
        ("Emotional Speech", test_emotions),
        ("Speed Control", test_speed_control),
        ("Voice Cloning", test_voice_cloning),
    ]
    
    print("\nAvailable tests:")
    for i, (name, _) in enumerate(tests, 1):
        print(f"{i}. {name}")
    print("6. Interactive Test")
    print("7. Run All Tests")
    
    choice = input("\nSelect test (1-7) [7]: ").strip() or "7"
    
    if choice == "6":
        interactive_test()
    elif choice == "7":
        for name, test_func in tests:
            try:
                test_func()
            except Exception as e:
                print(f"\n❌ Test '{name}' failed: {e}")
    else:
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(tests):
                tests[idx][1]()
            else:
                print("Invalid choice!")
        except ValueError:
            print("Invalid input!")
    
    print("\n" + "="*60)
    print("✅ Testing complete!")
    print("="*60)


if __name__ == "__main__":
    main()
