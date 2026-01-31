# 🤖 NVIDIA PersonaPlex - Hindi Guide

## Kya Hai Ye?

**NVIDIA PersonaPlex** ek powerful conversational AI model hai jo locally run hota hai. Ye **7 billion parameters** ka model hai jo natural conversations kar sakta hai.

## 🌟 Key Features

- ✅ **Full-Duplex** - Ek saath sun aur bol sakta hai
- ✅ **Natural Conversation** - Insaan jaisa baat karta hai
- ✅ **Customizable Personas** - Personality set kar sakte ho
- ✅ **Open Source** - Free aur modify kar sakte ho
- ✅ **Offline** - Internet ki zarurat nahi (download ke baad)
- ✅ **Low Latency** - Fast responses

## 📥 Installation

### Step 1: Dependencies Install Karo

```bash
pip install transformers torch accelerate
```

Ya:

```bash
pip install -r requirements.txt
```

### Step 2: System Requirements

**Minimum:**
- RAM: 16GB
- Disk Space: 20GB
- Python: 3.8+

**Best:**
- GPU: NVIDIA 8GB+ VRAM
- RAM: 32GB
- Disk: 30GB

## 🚀 Kaise Use Karein?

### Method 1: Direct Use

```python
from llm.personaplex_client import PersonaPlexClient

# Initialize
client = PersonaPlexClient()

# Persona set karo
client.set_persona("You are a helpful coding assistant")

# Response lo
response = client.generate("Python mein class kaise banate hain?")
print(response)
```

### Method 2: Agent Ke Saath

1. **`config.yaml` edit karo:**

```yaml
llm:
  provider: "personaplex"  # "ollama" se change karo
  model: "nvidia/personaplex-7b-v1"
```

2. **Agent run karo:**

```bash
python main.py
```

Done! Agent ab PersonaPlex use karega! 🎉

## 🎯 Features

### 1. Conversation History

PersonaPlex pichli baatein yaad rakhta hai:

```python
client.generate("Hello!")
# "Hi! How can I help?"

client.generate("2+2 kitna hota hai?")
# "2+2 equals 4"

client.generate("Thanks!")
# "You're welcome!"
```

### 2. Custom Personas

AI ki personality define karo:

```python
# Coding expert
client.set_persona("You are an expert Python developer")

# Creative writer
client.set_persona("You are a creative storyteller")

# Tech support
client.set_persona("You are a friendly tech support agent")
```

### 3. Memory Check

```python
# GPU memory dekho
mem = client.get_memory_usage()
print(f"Used: {mem['allocated_gb']} GB")
```

## 🧪 Testing

```bash
python test_personaplex.py
```

Ye karega:
1. Model download (pehli baar)
2. Load karega
3. Test conversations
4. Performance dikhayega

## ⚡ Performance

### GPU (RTX 3090)
- Load: ~30 seconds
- Response: ~0.5-2 seconds
- Memory: ~14GB VRAM

### CPU
- Load: ~60 seconds
- Response: ~5-10 seconds
- Memory: ~16GB RAM

## 🆚 PersonaPlex vs Ollama

| Feature | PersonaPlex | Ollama |
|---------|-------------|--------|
| Setup | Ek baar download | Install + models |
| Speed | Fast (GPU) | Very fast |
| Memory | 14GB | 4-8GB |
| Conversation | Natural | Standard |
| GPU | Recommended | Optional |

## 🔧 Common Issues

### Issue: Memory Kam Hai

**Solution:**
```python
# CPU use karo
client = PersonaPlexClient(device="cpu")

# Ya tokens kam karo
response = client.generate(prompt="...", max_new_tokens=256)
```

### Issue: CPU Par Slow Hai

**Solution:**
- GPU use karo
- Tokens reduce karo
- Temperature badhao

### Issue: Download Fail

**Solution:**
```bash
huggingface-cli login
huggingface-cli download nvidia/personaplex-7b-v1
```

## 💡 Best Practices

1. **GPU Use Karo** - 10x faster
2. **Personas Set Karo** - Better responses
3. **History Manage Karo** - Clear when needed
4. **Memory Monitor Karo** - Check usage
5. **Tokens Optimize Karo** - Appropriate size

## 📚 Examples

### Example 1: Code Generate

```python
client.set_persona("You are a Python expert")
code = client.generate("String reverse karne ka function likho")
```

### Example 2: Story Writing

```python
client.set_persona("You are a creative writer")
story = client.generate(
    "Ek sci-fi story likho",
    temperature=0.9,
    max_new_tokens=1024
)
```

### Example 3: Tech Help

```python
client.set_persona("You are tech support")
help = client.generate("Mera computer start nahi ho raha")
```

## 📁 Files Created

1. ✅ `llm/personaplex_client.py` - Main client
2. ✅ `test_personaplex.py` - Test script
3. ✅ `PERSONAPLEX_GUIDE.md` - Full docs
4. ✅ `PERSONAPLEX_HINDI.md` - Ye file
5. ✅ Updated `config.yaml` - Config options
6. ✅ Updated `requirements.txt` - Dependencies

## ✅ Quick Start

```bash
# 1. Dependencies install
pip install transformers torch accelerate

# 2. Test
python test_personaplex.py

# 3. Agent mein use
# config.yaml mein provider = "personaplex" set karo
python main.py
```

## 🎉 Conclusion

PersonaPlex ek powerful conversational AI hai jo:

- ✨ Natural conversations karta hai
- 🧠 Smart reasoning hai
- 🎭 Personas support karta hai
- 🚀 Fast responses deta hai
- 💻 Locally run hota hai

**Try karo aur experience karo next-level AI!** 🤖✨

---

**Note**: Pehli baar ~14GB download hoga. Patience rakho! ⏳

---

*Last Updated: 2026-01-27*
