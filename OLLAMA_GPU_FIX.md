# Ollama GPU Fix for RTX 2050 🎮

## Current Status
✅ **GPU Detected:** NVIDIA GeForce RTX 2050
✅ **VRAM:** 4096 MB
✅ **CUDA:** 13.0
✅ **Driver:** 581.83

## Problem
Ollama might be using CPU instead of GPU.

## Solution: Force Ollama to Use GPU

### Step 1: Set Environment Variable
```powershell
# In PowerShell (Admin):
[System.Environment]::SetEnvironmentVariable("OLLAMA_GPU", "1", "User")
[System.Environment]::SetEnvironmentVariable("CUDA_VISIBLE_DEVICES", "0", "User")
```

### Step 2: Restart Ollama Service
```powershell
# Stop Ollama
taskkill /F /IM ollama.exe

# Wait 5 seconds

# Start Ollama
ollama serve
```

### Step 3: Test GPU Usage
```powershell
# In another terminal, run:
ollama run qwen2.5-coder:7b "Write a Python hello world"

# Then check GPU usage:
nvidia-smi
```

You should see `ollama` process using GPU memory!

---

## Alternative: Use Ollama with GPU Layers

Create a Modelfile to force GPU usage:

```modelfile
FROM qwen2.5-coder:7b

# Force all layers on GPU
PARAMETER num_gpu 99
```

Save as `Modelfile`, then:
```powershell
ollama create qwen-gpu -f Modelfile
ollama run qwen-gpu
```

---

## Quick Test Script

```python
# test_ollama_gpu.py
import subprocess
import time

print("Testing Ollama GPU usage...")
print("Starting inference...")

# Run ollama
proc = subprocess.Popen(
    ["ollama", "run", "qwen2.5-coder:7b", "print hello world in python"],
    stdout=subprocess.PIPE
)

# Wait a bit
time.sleep(2)

# Check GPU
gpu_check = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
print("\n" + gpu_check.stdout)

if "ollama" in gpu_check.stdout.lower():
    print("✅ Ollama is using GPU!")
else:
    print("❌ Ollama is NOT using GPU")

proc.wait()
```

---

## Expected nvidia-smi Output (When Working)

```
+-----------------------------------------------------------------------------------------+
| Processes:                                                                              |
|  GPU   GI   CI        PID   Type   Process name                            GPU Memory |
|        ID   ID                                                               Usage      |
|=========================================================================================|
|    0   N/A  N/A      12345    C   ollama.exe                                  2500MiB  |
+-----------------------------------------------------------------------------------------+
```

---

## If Still Using CPU

### Check Ollama Logs:
```powershell
# Windows Event Viewer or check:
Get-EventLog -LogName Application -Source Ollama -Newest 10
```

### Reinstall Ollama with GPU Support:
```powershell
# Uninstall
winget uninstall Ollama.Ollama

# Reinstall (will auto-detect GPU)
winget install Ollama.Ollama

# Verify
ollama --version
```

---

## For Your Agent

Once Ollama uses GPU, update config:

```yaml
llm:
  provider: "ollama"
  model: "qwen2.5-coder:7b"  # Will use GPU automatically
  base_url: "http://127.0.0.1:11434"
```

Then run:
```powershell
python main.py
```

Monitor GPU usage while agent runs:
```powershell
# In another terminal:
nvidia-smi -l 1  # Update every 1 second
```

---

## Performance on RTX 2050

| Model | VRAM Usage | Tokens/sec | Quality |
|-------|------------|------------|---------|
| qwen2.5-coder:7b (GPU) | ~3.5GB | ~20-30 | 🧠🧠🧠🧠🧠 |
| qwen2.5-coder:7b (CPU) | 0MB | ~2-5 | 🧠🧠🧠🧠🧠 |

**10x faster on GPU!** 🚀

---

## Troubleshooting

### "CUDA out of memory"
- Close other GPU apps (browsers, games)
- Use smaller model: `qwen2.5:3b`

### "Ollama not found"
- Restart terminal
- Check PATH: `where ollama`

### Still slow?
- Check Task Manager → GPU usage
- Ensure no other process using GPU
- Try `ollama pull qwen2.5:3b` (smaller model)

---

## Next Steps

1. Set environment variables
2. Restart Ollama
3. Test with `ollama run qwen2.5-coder:7b "test"`
4. Check `nvidia-smi` for GPU usage
5. Run agent: `python main.py`

GPU lag jayega! 🎮
