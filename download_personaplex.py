"""
Quick PersonaPlex Download & Test

This script will:
1. Download PersonaPlex model (~14GB)
2. Load it with 8-bit optimization
3. Test basic conversation
"""

import sys
sys.path.insert(0, '.')

print("=" * 70)
print("🤖 NVIDIA PersonaPlex - Download & Setup")
print("=" * 70)

# Check dependencies
print("\n📦 Checking dependencies...")
try:
    import torch
    print("✅ PyTorch installed")
    
    import transformers
    print("✅ Transformers installed")
    
    import accelerate
    print("✅ Accelerate installed")
    
    import bitsandbytes
    print("✅ BitsAndBytes installed (for 8-bit)")
    
except ImportError as e:
    print(f"\n❌ Missing dependency: {e}")
    print("\n💡 Install with:")
    print("   pip install transformers torch accelerate bitsandbytes")
    sys.exit(1)

# Check GPU
print("\n🎮 Checking GPU...")
if torch.cuda.is_available():
    gpu_name = torch.cuda.get_device_name(0)
    vram_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
    print(f"✅ GPU Found: {gpu_name}")
    print(f"✅ VRAM: {vram_gb:.1f} GB")
    
    if vram_gb < 7:
        print(f"\n⚠️  Warning: {vram_gb:.1f}GB VRAM might be tight!")
        print("   Recommended: 8GB+ for 8-bit mode")
        print("   Consider using CPU mode if it fails")
    elif vram_gb < 12:
        print(f"\n✅ Perfect! {vram_gb:.1f}GB is good for 8-bit mode")
    else:
        print(f"\n🎉 Excellent! {vram_gb:.1f}GB can run standard mode")
else:
    print("⚠️  No GPU found - will use CPU (slower)")

# Download and load model
print("\n" + "=" * 70)
print("📥 Downloading PersonaPlex Model")
print("=" * 70)
print("\n⚠️  IMPORTANT:")
print("   - First download: ~14GB (one-time)")
print("   - Takes 10-30 minutes depending on internet")
print("   - Model will be cached for future use")
print("   - Be patient! ☕")
print("\n🔄 Starting download...\n")

try:
    from llm.personaplex_optimized import PersonaPlexClientOptimized
    
    # This will download the model
    client = PersonaPlexClientOptimized(
        model_name="nvidia/personaplex-7b-v1",
        device="auto",
        use_8bit=True
    )
    
    print("\n" + "=" * 70)
    print("✅ Model Downloaded & Loaded Successfully!")
    print("=" * 70)
    
    # Show info
    info = client.get_model_info()
    print(f"\n📊 Model Info:")
    print(f"   Name: {info['model_name']}")
    print(f"   Device: {info['device']}")
    print(f"   Quantization: {info['quantization']}")
    print(f"   Optimized for: {info['optimized_for']}")
    
    # Show memory
    if torch.cuda.is_available():
        mem = client.get_memory_usage()
        print(f"\n💾 VRAM Usage:")
        print(f"   Used: {mem['allocated_gb']} GB")
        print(f"   Total: {mem['total_gb']} GB")
        print(f"   Free: {mem['free_gb']} GB")
        
        if mem['free_gb'] < 0.5:
            print("\n⚠️  Low VRAM! Close other apps if needed.")
    
    # Test conversation
    print("\n" + "=" * 70)
    print("💬 Testing Conversation")
    print("=" * 70)
    
    client.set_persona("You are a helpful AI assistant")
    
    test_prompts = [
        "Hello! What can you do?",
        "Tell me a fun fact about AI"
    ]
    
    for prompt in test_prompts:
        print(f"\n👤 User: {prompt}")
        response = client.generate(
            prompt=prompt,
            max_new_tokens=128,
            temperature=0.7
        )
        print(f"🤖 PersonaPlex: {response}")
    
    print("\n" + "=" * 70)
    print("🎉 SUCCESS! PersonaPlex is ready to use!")
    print("=" * 70)
    print("\n✅ Next steps:")
    print("   1. Model is downloaded and cached")
    print("   2. Config is already set to use PersonaPlex")
    print("   3. Run: python main.py")
    print("   4. Agent will use PersonaPlex automatically!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\n💡 Troubleshooting:")
    print("   1. Check internet connection")
    print("   2. Ensure enough disk space (~20GB)")
    print("   3. Try again - downloads can be resumed")
    print("   4. Check VRAM usage (close other apps)")
    
    import traceback
    print("\n📋 Full error:")
    traceback.print_exc()
