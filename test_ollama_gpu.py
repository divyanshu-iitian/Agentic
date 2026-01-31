# Test Ollama GPU Usage
import subprocess
import time

print("🎮 Testing if Ollama uses your RTX 2050...")
print("\n1. Starting Ollama inference...")

# Start ollama in background
proc = subprocess.Popen(
    ["ollama", "run", "qwen2.5-coder:7b", "write hello world in python"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

# Wait for model to load
print("   Waiting for model to load...")
time.sleep(3)

# Check GPU
print("\n2. Checking GPU usage with nvidia-smi...")
result = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
output = result.stdout

print("\n" + "="*80)
print(output)
print("="*80)

# Parse output
if "ollama" in output.lower() or "MiB" in output:
    lines = output.split('\n')
    for line in lines:
        if 'MiB' in line and '0MiB' not in line:
            print("\n✅ SUCCESS! Ollama is using GPU!")
            print(f"   GPU Memory in use: {line.strip()}")
            break
    else:
        print("\n⚠️  Ollama might be loading... Check nvidia-smi manually")
else:
    print("\n❌ Ollama not detected in GPU processes")

# Cleanup
proc.terminate()
print("\n3. Test complete!")
