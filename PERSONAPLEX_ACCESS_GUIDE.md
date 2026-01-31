# PersonaPlex Access Guide 🔐

## Problem
PersonaPlex ek **gated model** hai HuggingFace par. Iska matlab hai ki aapko pehle access request karni hogi.

## Solution: Step-by-Step Guide

### Step 1: HuggingFace Account Banao
1. **Website kholo**: https://huggingface.co/join
2. **Sign up karo** with email/GitHub/Google
3. **Email verify karo**

### Step 2: PersonaPlex Access Request Karo
1. **Model page kholo**: https://huggingface.co/nvidia/personaplex-7b-v1
2. **"Request Access" button** par click karo
3. **Form fill karo**:
   - Name
   - Organization (optional - "Personal" likh sakte ho)
   - Use case (kuch bhi likh do, jaise "AI research" ya "Desktop automation")
4. **Submit karo**
5. **Wait karo** - NVIDIA team approve karegi (usually 1-2 days)

### Step 3: HuggingFace Token Generate Karo
1. **Settings kholo**: https://huggingface.co/settings/tokens
2. **"New token" par click karo**
3. **Token name do**: "PersonaPlex Access"
4. **Type select karo**: "Read" (write ki zarurat nahi)
5. **Generate karo**
6. **Token copy karo** - ye ek baar hi dikhega!

### Step 4: Token Ko System Mein Add Karo

#### Option A: Environment Variable (Recommended)
```powershell
# PowerShell mein run karo:
$env:HF_TOKEN = "your_token_here"

# Permanent karne ke liye:
[System.Environment]::SetEnvironmentVariable("HF_TOKEN", "your_token_here", "User")
```

#### Option B: HuggingFace CLI
```bash
# Install CLI
pip install huggingface-hub

# Login karo
huggingface-cli login

# Token paste karo jab puche
```

#### Option C: Code Mein Directly (Not Recommended)
`.env` file mein add karo:
```
HF_TOKEN=your_token_here
```

### Step 5: Verify Access
```python
# Test script
from transformers import AutoTokenizer

try:
    tokenizer = AutoTokenizer.from_pretrained(
        "nvidia/personaplex-7b-v1",
        trust_remote_code=True,
        token="your_token_here"  # Ya environment variable use karo
    )
    print("✅ Access successful!")
except Exception as e:
    print(f"❌ Error: {e}")
```

### Step 6: Config Update Karo
Agar access mil gaya, toh `config.yaml` mein:
```yaml
llm:
  provider: "personaplex"
  model: "nvidia/personaplex-7b-v1"
```

## Current Status ⚠️

**Abhi aapke paas PersonaPlex access NAHI hai.**

Isliye maine config ko **Ollama** par switch kar diya hai jo:
- ✅ Local hai
- ✅ No authentication needed
- ✅ Fast and reliable
- ✅ Works offline

## Recommendation 💡

### Option 1: Use Ollama (Current - Works Now)
```yaml
llm:
  provider: "ollama"
  model: "qwen2.5:3b"
```
**Pros:**
- Immediately works
- No authentication
- Fully local
- Fast

**Cons:**
- Smaller model than PersonaPlex

### Option 2: Wait for PersonaPlex Access
1. Request access (steps above)
2. Wait for approval (1-2 days)
3. Add HF token
4. Switch config back to PersonaPlex

**Pros:**
- Larger, more capable model (7B vs 3B)
- Better at complex reasoning

**Cons:**
- Requires internet for first download
- Needs HuggingFace account
- Approval wait time
- More VRAM needed

## Quick Commands

### Check if Ollama is running:
```powershell
curl http://localhost:11434
```

### Pull Qwen model (if not already):
```powershell
ollama pull qwen2.5:3b
```

### Test the agent:
```powershell
python main.py
```

## Troubleshooting

### Error: "Cannot access gated repo"
- ❌ PersonaPlex access nahi mila
- ✅ Solution: Use Ollama (already configured)

### Error: "Ollama connection refused"
- ❌ Ollama server nahi chal raha
- ✅ Solution: `ollama serve` run karo

### Error: "Model not found"
- ❌ Model download nahi hua
- ✅ Solution: `ollama pull qwen2.5:3b`

## Next Steps

**For now (Recommended):**
1. ✅ Config already switched to Ollama
2. ✅ Run the agent: `python main.py`
3. ✅ Test browser intelligence

**For PersonaPlex (Later):**
1. Request access: https://huggingface.co/nvidia/personaplex-7b-v1
2. Wait for approval
3. Generate HF token
4. Update config
5. Restart agent

---

**Current Status:** Agent is ready to run with **Ollama + Qwen2.5:3b** 🚀
