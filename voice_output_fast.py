"""
Simple Fast Voice Output - pyttsx3

Terminal mein text likho, instantly voice mein sunao.
Lightweight and fast!

Usage: python voice_output_fast.py
"""

import sys

print("Initializing voice engine...")

try:
    import pyttsx3
    
    # Initialize TTS engine
    engine = pyttsx3.init()
    
    # Configure voice
    voices = engine.getProperty('voices')
    engine.setProperty('rate', 175)  # Speed of speech
    engine.setProperty('volume', 1.0)  # Volume (0.0 to 1.0)
    
    print("✅ Voice engine ready!")
    
except ImportError:
    print("❌ Error: pyttsx3 not installed!")
    print("Install with: pip install pyttsx3")
    sys.exit(1)


def text_to_speech(text: str):
    """
    Convert text to speech and play it instantly.
    
    Args:
        text: Text to speak
    """
    try:
        print(f"🔊 Speaking: '{text}'")
        engine.say(text)
        engine.runAndWait()
        print("✅ Done!\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def list_voices():
    """List available voices."""
    print("\n📢 Available Voices:")
    voices = engine.getProperty('voices')
    for i, voice in enumerate(voices):
        print(f"  {i}: {voice.name}")
    print()


def change_voice(voice_index: int):
    """Change voice."""
    try:
        voices = engine.getProperty('voices')
        if 0 <= voice_index < len(voices):
            engine.setProperty('voice', voices[voice_index].id)
            print(f"✅ Voice changed to: {voices[voice_index].name}\n")
        else:
            print("❌ Invalid voice index\n")
    except Exception as e:
        print(f"❌ Error: {e}\n")


def change_speed(rate: int):
    """Change speaking speed."""
    try:
        engine.setProperty('rate', rate)
        print(f"✅ Speed changed to: {rate} words per minute\n")
    except Exception as e:
        print(f"❌ Error: {e}\n")


def main():
    """Main loop - keep accepting text input."""
    print("\n" + "="*60)
    print("🎙️ FAST VOICE OUTPUT - Instant Text-to-Speech")
    print("="*60)
    print("\nCommands:")
    print("  - Type any text to hear it spoken instantly")
    print("  - Type 'quit' or 'exit' to stop")
    print("  - Type 'voices' to see available voices")
    print("  - Type 'voice <number>' to change voice")
    print("  - Type 'speed <number>' to change speed (default: 175)")
    print("  - Type 'help' for more info")
    print("\n" + "="*60 + "\n")
    
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
                print("  • Adjust speed: 'speed 150' (slow) to 'speed 200' (fast)")
                print("  • Change voice: 'voices' then 'voice <number>'")
                print("  • Hindi support: Type in Devanagari script")
                print("  • Exit: Type 'quit' or press Ctrl+C\n")
                continue
            
            # Show available voices
            if user_input.lower() == 'voices':
                list_voices()
                continue
            
            # Change voice
            if user_input.lower().startswith('voice '):
                try:
                    voice_num = int(user_input.split()[1])
                    change_voice(voice_num)
                except:
                    print("❌ Usage: voice <number>\n")
                continue
            
            # Change speed
            if user_input.lower().startswith('speed '):
                try:
                    speed = int(user_input.split()[1])
                    change_speed(speed)
                except:
                    print("❌ Usage: speed <number>\n")
                continue
            
            # Empty input
            if not user_input:
                continue
            
            # Generate and play speech
            text_to_speech(user_input)
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}\n")


if __name__ == "__main__":
    main()
