# GPU Performance Test - CPU vs GPU
import subprocess
import time

print("="*80)
print("🎮 OLLAMA GPU TEST - RTX 2050")
print("="*80)

print("\n📊 Testing inference speed to prove GPU usage...\n")

# Test prompt
prompt = "Write a Python function to sort a list"

print("🚀 Running inference with qwen2.5-coder:7b...")
print(f"   Prompt: '{prompt}'")
print("\n⏱️  Measuring response time...\n")

# Time the inference
start = time.time()

result = subprocess.run(
    ["ollama", "run", "qwen2.5-coder:7b", prompt],
    capture_output=True,
    text=True,
    timeout=30
)

end = time.time()
elapsed = end - start

print("="*80)
print("📈 RESULTS:")
print("="*80)
print(f"\n⏱️  Response Time: {elapsed:.2f} seconds")
print(f"📝 Response Length: {len(result.stdout)} characters")

# Calculate tokens/sec (rough estimate)
tokens = len(result.stdout.split())
tokens_per_sec = tokens / elapsed if elapsed > 0 else 0

print(f"🔢 Estimated Tokens: {tokens}")
print(f"⚡ Tokens/Second: {tokens_per_sec:.1f}")

print("\n" + "="*80)
print("💡 INTERPRETATION:")
print("="*80)

if tokens_per_sec > 15:
    print("✅ GPU MODE - Fast! (15+ tokens/sec)")
    print("   Your RTX 2050 is being used! 🎮")
elif tokens_per_sec > 5:
    print("⚠️  MIXED MODE - Moderate (5-15 tokens/sec)")
    print("   GPU might be partially used")
else:
    print("❌ CPU MODE - Slow (<5 tokens/sec)")
    print("   GPU is NOT being used")

print("\n" + "="*80)
print("🔍 BENCHMARK REFERENCE:")
print("="*80)
print("CPU-only (slow):     2-5 tokens/sec")
print("GPU RTX 2050 (fast): 20-40 tokens/sec")
print("="*80)

print("\n📋 Response Preview:")
print("-"*80)
print(result.stdout[:500])
print("-"*80)
