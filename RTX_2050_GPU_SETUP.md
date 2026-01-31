# GPU Setup Guide for RTX 2050 🎮

## Problem
Your PyTorch installation doesn't have CUDA support. It's CPU-only.

## Solution: Install CUDA-Enabled PyTorch

### Step 1: Uninstall Current PyTorch
```powershell
python -m pip uninstall -y torch torchvision torchaudio
```

### Step 2: Install CUDA-Enabled PyTorch
```powershell
# For CUDA 11.8 (Most compatible with RTX 2050)
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# OR for CUDA 12.1 (Newer, if you have latest drivers)
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### Step 3: Verify GPU Detection
```powershell
python -c "import torch; print('CUDA Available:', torch.cuda.is_available()); print('GPU Name:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')"
```

Expected output:
```
CUDA Available: True
GPU Name: NVIDIA GeForce RTX 2050
```

---

## RTX 2050 Specs
- **VRAM:** 4GB GDDR6
- **CUDA Cores:** 2048
- **Compute Capability:** 8.6
- **Good for:** PersonaPlex with 8-bit quantization

---

## PersonaPlex on RTX 2050

### Memory Requirements:
- **Full Precision (FP16):** ~14GB VRAM ❌ (Too much for 4GB)
- **8-bit Quantization:** ~7GB VRAM ❌ (Still too much)
- **4-bit Quantization:** ~3.5GB VRAM ✅ (Will fit!)

### Recommendation:
Use **4-bit quantization** for RTX 2050:

```python
# In personaplex_client.py or create personaplex_4bit.py
from transformers import AutoModelForCausalLM, BitsAndBytesConfig

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4"
)

model = AutoModelForCausalLM.from_pretrained(
    "nvidia/personaplex-7b-v1",
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
    token=hf_token
)
```

---

## Better Alternative for RTX 2050: Use Ollama!

**Why Ollama is Better for 4GB VRAM:**
- ✅ **Optimized for low VRAM**
- ✅ **Automatic quantization**
- ✅ **Faster inference**
- ✅ **No manual setup**
- ✅ **Works out of the box**

### Install Ollama:
```powershell
# Download from: https://ollama.com/download
# Or use winget:
winget install Ollama.Ollama
```

### Pull Model:
```powershell
ollama pull qwen2.5:3b   # Fast, 2GB
ollama pull qwen2.5:7b   # Powerful, 4.7GB (might need CPU offloading)
```

### Update Config:
```yaml
llm:
  provider: "ollama"
  model: "qwen2.5:3b"  # Best for 4GB VRAM
```

---

## Performance Comparison on RTX 2050

| Setup | VRAM Usage | Speed | Quality |
|-------|------------|-------|---------|
| PersonaPlex (4-bit) | ~3.5GB | ⚡⚡ | 🧠🧠🧠🧠 |
| Qwen 2.5:3b (Ollama) | ~2GB | ⚡⚡⚡⚡⚡ | 🧠🧠🧠🧠 |
| Qwen 2.5:7b (Ollama) | ~4.5GB | ⚡⚡⚡ | 🧠🧠🧠🧠🧠 |

**Winner for RTX 2050:** Qwen 2.5:3b via Ollama

---

## Quick Fix Commands

### Option 1: Install CUDA PyTorch (For PersonaPlex)
```powershell
python -m pip uninstall -y torch torchvision torchaudio
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
python -m pip install bitsandbytes  # For 4-bit quantization
```

### Option 2: Switch to Ollama (Recommended)
```powershell
# Install Ollama
winget install Ollama.Ollama

# Pull model
ollama pull qwen2.5:3b

# Update config.yaml
# Change provider to "ollama"
# Change model to "qwen2.5:3b"

# Run agent
python main.py
```

---

## My Recommendation 💡

**For RTX 2050 (4GB VRAM), use Ollama with Qwen 2.5:3b:**

1. ✅ **Fastest** - Optimized for GPU
2. ✅ **Most reliable** - No memory issues
3. ✅ **Best performance** - Faster than PersonaPlex 4-bit
4. ✅ **Easiest setup** - No CUDA installation needed

**PersonaPlex is overkill** for desktop automation. Qwen 2.5:3b is perfect!

---

## Current Status

❌ **PyTorch:** CPU-only (no CUDA)
❌ **PersonaPlex:** Can't run without GPU PyTorch
✅ **Solution:** Install CUDA PyTorch OR switch to Ollama

**Next Step:** Choose Option 1 or Option 2 above!
