"""
Simple Voice Output Script - Using Bark Engine

Terminal mein text likho, bark engine voice mein bolega.
Uses existing voice engine with bark support.

Usage: python voice_output_simple.py
"""

import sys
from voice.voice_engine import VoiceEngine

print("Initializing Bark voice engine...")

try:
    # Initialize voice engine
    engine = VoiceEngine()
    
    # Check if bark is available
    if "bark" not in engine.available_models:
        print("❌ Bark not available!")
        print("Available models:", engine.available_models)
        print("\nInstall bark with:")
        print("  pip install git+https://github.com/suno-ai/bark.git")
        sys.exit(1)
    
    print("✅ Bark ready!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)


def text_to_speech(text: str, emotion: str = None):
    """
    Convert text to speech using Bark engine.
    
    Args:
        text: Text to speak
        emotion: Optional emotion (happy, sad, angry, excited)
    """
    try:
        print(f"\n🔊 Speaking: '{text}'")
        if emotion:
            print(f"   Emotion: {emotion}")
        
        # Generate and play audio using bark
        engine.speak(text, model="bark", emotion=emotion, blocking=True)
        
        print("✅ Done!\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Main loop - keep accepting text input."""
    print("\n" + "="*60)
    print("🎙️ BARK VOICE OUTPUT - Text-to-Speech")
    print("="*60)
    print("\nCommands:")
    print("  - Type any text to hear it spoken")
    print("  - Type 'quit' or 'exit' to stop")
    print("  - Type 'emotion <text>' for emotional speech")
    print("    Examples:")
    print("      emotion happy Hello! How are you?")
    print("      emotion sad I'm feeling down today")
    print("      emotion angry This is unacceptable!")
    print("\n" + "="*60 + "\n")
    
    current_emotion = None
    
    while True:
        try:
            # Get input
            user_input = input("💬 You: ").strip()
            
            # Check for exit
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            # Help
            if user_input.lower() == 'help':
                print("\n📖 Help:")
                print("  • Type any text and press Enter to hear it")
                print("  • Add emotion: 'emotion happy <text>'")
                print("  • Supported emotions: happy, sad, angry, excited, calm")
                print("  • Exit: Type 'quit' or press Ctrl+C\n")
                continue
            
            # Emotion command
            if user_input.lower().startswith('emotion '):
                try:
                    parts = user_input.split(maxsplit=2)
                    if len(parts) >= 3:
                        emotion_type = parts[1].lower()
                        text = parts[2]
                        text_to_speech(text, emotion=emotion_type)
                    else:
                        print("❌ Usage: emotion <type> <text>\n")
                except Exception as e:
                    print(f"❌ Error: {e}\n")
                continue
            
            # Empty input
            if not user_input:
                continue
            
            # Generate and play speech
            text_to_speech(user_input, emotion=current_emotion)
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}\n")


if __name__ == "__main__":
    main()
