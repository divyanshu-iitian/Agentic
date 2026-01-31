"""
Test NVIDIA PersonaPlex Integration

This script tests the PersonaPlex model locally.
"""

import sys
sys.path.insert(0, '.')

from llm.personaplex_client import PersonaPlexClient
from utils.logger import log


def test_personaplex():
    """Test PersonaPlex model"""
    print("=" * 60)
    print("🤖 NVIDIA PersonaPlex Test")
    print("=" * 60)
    
    try:
        # Initialize client
        print("\n📥 Loading PersonaPlex model...")
        print("⚠️  This will download ~14GB model on first run")
        print("⏳ Please wait...")
        
        client = PersonaPlexClient(
            model_name="nvidia/personaplex-7b-v1",
            device="auto"
        )
        
        # Show model info
        info = client.get_model_info()
        print("\n✅ Model loaded successfully!")
        print(f"\n📊 Model Info:")
        print(f"  Name: {info['model_name']}")
        print(f"  Device: {info['device']}")
        print(f"  Parameters: {info['parameters']}")
        print(f"  Type: {info['type']}")
        
        # Check GPU
        if client.check_gpu_available():
            print(f"\n🎮 GPU Available: Yes")
            mem = client.get_memory_usage()
            print(f"  Memory Allocated: {mem['allocated_gb']} GB")
            print(f"  Memory Reserved: {mem['reserved_gb']} GB")
        else:
            print(f"\n💻 Running on CPU")
        
        # Test conversation
        print("\n" + "=" * 60)
        print("💬 Testing Conversation")
        print("=" * 60)
        
        # Set persona
        client.set_persona("You are a helpful AI coding assistant")
        
        # Test prompts
        test_prompts = [
            "Hello! Can you help me with Python?",
            "What's the best way to handle errors in Python?",
            "Thanks for the help!"
        ]
        
        for i, prompt in enumerate(test_prompts, 1):
            print(f"\n👤 User: {prompt}")
            response = client.generate(
                prompt=prompt,
                max_new_tokens=256,
                temperature=0.7
            )
            print(f"🤖 PersonaPlex: {response}")
        
        print("\n" + "=" * 60)
        print("✅ Test completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Make sure you have:")
        print("  1. Installed dependencies: pip install transformers torch accelerate")
        print("  2. Enough disk space (~14GB for model)")
        print("  3. GPU with CUDA (recommended) or sufficient RAM for CPU")
        return False
    
    return True


if __name__ == "__main__":
    test_personaplex()
