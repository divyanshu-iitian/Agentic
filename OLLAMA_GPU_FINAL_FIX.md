# FINAL SOLUTION - Ollama GPU Fix 🎯

## Discovery ✅

Your Ollama HAS CUDA support!
```
cudart64_12.dll     - CUDA Runtime
ggml-cuda.dll       - GPU acceleration library
```

## Problem 🤔

Ollama has GPU support but might not be using it due to:
1. Environment variables not set
2. Ollama service needs restart
3. ROCm/CPU fallback enabled

## SOLUTION (Step-by-Step)

### Step 1: Stop Ollama Completely
```powershell
# Kill all Ollama processes
Get-Process ollama* | Stop-Process -Force

# Wait 5 seconds
Start-Sleep -Seconds 5
```

### Step 2: Set Environment Variables (CRITICAL)
```powershell
# Force GPU usage
[System.Environment]::SetEnvironmentVariable("OLLAMA_NUM_GPU", "1", "User")
[System.Environment]::SetEnvironmentVariable("OLLAMA_GPU_OVERHEAD", "0", "User")

# Restart your terminal after this!
```

### Step 3: Restart Ollama
```powershell
# Start Ollama service
Start-Process "C:\Users\user\AppData\Local\Programs\Ollama\ollama.exe" -ArgumentList "serve"

# Wait for it to start
Start-Sleep -Seconds 3
```

### Step 4: Test GPU Usage
```powershell
# Quick test
ollama run qwen2.5-coder:7b "hello"

# Should be FAST (1-2 seconds)
```

### Step 5: Verify with Task Manager
```
1. Open Task Manager (Ctrl+Shift+Esc)
2. Performance tab
3. GPU 0 - NVIDIA GeForce RTX 2050
4. Run: ollama run qwen2.5-coder:7b "test"
5. Watch "Compute" or "3D" graph - should spike!
```

---

## Quick Fix Script

Save as `fix_ollama_gpu.ps1`:

```powershell
# Stop Ollama
Write-Host "Stopping Ollama..." -ForegroundColor Yellow
Get-Process ollama* -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 3

# Set environment variables
Write-Host "Setting GPU environment variables..." -ForegroundColor Yellow
[System.Environment]::SetEnvironmentVariable("OLLAMA_NUM_GPU", "1", "User")
[System.Environment]::SetEnvironmentVariable("OLLAMA_GPU_OVERHEAD", "0", "User")

# Restart Ollama
Write-Host "Starting Ollama..." -ForegroundColor Yellow
Start-Process "C:\Users\user\AppData\Local\Programs\Ollama\ollama.exe" -ArgumentList "serve"
Start-Sleep -Seconds 5

Write-Host "✅ Done! Test with: ollama run qwen2.5-coder:7b 'hello'" -ForegroundColor Green
Write-Host "⚠️  Close and reopen your terminal for env vars to take effect!" -ForegroundColor Cyan
```

Run:
```powershell
powershell -ExecutionPolicy Bypass -File fix_ollama_gpu.ps1
```

---

## Alternative: Reinstall Ollama (Nuclear Option)

If above doesn't work:

```powershell
# Uninstall
winget uninstall Ollama.Ollama

# Reinstall (will auto-detect GPU)
winget install Ollama.Ollama

# Pull model again
ollama pull qwen2.5-coder:7b
```

---

## How to Know if GPU is Working

### Method 1: Speed Test
```
CPU: 10-30 seconds for simple prompt
GPU: 1-3 seconds for simple prompt
```

### Method 2: Task Manager
- GPU Compute/3D usage spikes during inference

### Method 3: Check Ollama Logs
```powershell
# Enable debug mode
$env:OLLAMA_DEBUG=1
ollama serve

# In another terminal:
ollama run qwen2.5-coder:7b "test"

# Look for "CUDA" or "GPU" in logs
```

---

## Expected Behavior (GPU Working)

```powershell
PS> ollama run qwen2.5-coder:7b "print hello"
⠋  # Loading (1-2 sec)
print("Hello, World!")  # Response (instant)
```

**Total time: 2-3 seconds** ✅

---

## Current Status

✅ GPU: RTX 2050 detected
✅ Drivers: 581.83 installed
✅ CUDA: 13.0 available
✅ Ollama: Has CUDA DLLs
❓ GPU Usage: Needs environment variables set

**Next Step:** Run the fix script above!
