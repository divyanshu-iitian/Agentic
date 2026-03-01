"""
Terminal Voice Output - Bark Engine

Simple script: Terminal mein type karo, Bark human-like voice mein bolega!
Bark models pehli baar download honge (~1GB), phir fast.

Usage: python speak.py
"""

import sys
import warnings
warnings.filterwarnings('ignore')

print("\n" + "="*60)
print("🎙️ Loading Bark Engine...")
print("="*60)
print("(First time will download models ~1GB, please wait...)\n")

try:
    import torch
    import numpy as np
    
    # Fix PyTorch 2.6 weights_only issue with Bark models
    # Monkey-patch torch.load to use weights_only=False (Bark models are trusted)
    _original_torch_load = torch.load
    def _patched_torch_load(*args, **kwargs):
        if 'weights_only' not in kwargs:
            kwargs['weights_only'] = False
        return _original_torch_load(*args, **kwargs)
    torch.load = _patched_torch_load
    
    from bark import SAMPLE_RATE, generate_audio, preload_models
    import sounddevice as sd
    
    # Preload for faster generation
    print("⏳ Loading models...")
    preload_models()
    print("✅ Bark Ready!\n")
    
except ImportError as e:
    print(f"❌ Error: {e}")
    print("\nMissing module. Try:")
    print("  pip install git+https://github.com/suno-ai/bark.git")
    print("  pip install sounddevice")
    sys.exit(1)


def speak(text: str):
    """Generate and play speech"""
    try:
        print(f"🎤 Speaking: '{text}'")
        
        # Generate audio (takes 5-10 seconds)
        audio = generate_audio(text)
        
        # Play
        sd.play(audio, SAMPLE_RATE)
        sd.wait()
        
        print("✅ Done!\n")
        
    except Exception as e:
        print(f"❌ Error: {e}\n")


def main():
    print("="*60)
    print("Commands:")
    print("  - Type text to hear it in human voice")
    print("  - Type 'quit' to exit")
    print("  - Add [laughs] [sighs] etc for emotions")
    print("="*60 + "\n")
    
    while True:
        try:
            text = input("💬 You: ").strip()
            
            if text.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            if not text:
                continue
            
            speak(text)
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}\n")


if __name__ == "__main__":
    main()
