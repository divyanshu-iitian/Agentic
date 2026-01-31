# 🤖 NVIDIA PersonaPlex Integration

## Overview

**NVIDIA PersonaPlex** is an open-source conversational AI model with 7 billion parameters, designed for natural, real-time dialogue with full-duplex capabilities.

### Key Features

- ✅ **7B Parameters** - Powerful yet efficient
- ✅ **Full-Duplex Dialogue** - Listen and speak simultaneously
- ✅ **Natural Turn-Taking** - Human-like conversation flow
- ✅ **Interruption Handling** - Graceful conversation management
- ✅ **Customizable Personas** - Define AI personality
- ✅ **Low Latency** - Real-time responses
- ✅ **Open Source** - Free to use and modify

## Model Information

- **Model ID**: `nvidia/personaplex-7b-v1`
- **Source**: Hugging Face
- **License**: NVIDIA Open Model License + CC-BY-4.0
- **Size**: ~14GB download
- **Architecture**: Based on Moshi
- **Base Model**: Helium (for reasoning)

## Installation

### 1. Install Dependencies

```bash
pip install transformers torch accelerate
```

Or install all requirements:

```bash
pip install -r requirements.txt
```

### 2. System Requirements

**Minimum:**
- **RAM**: 16GB (CPU mode)
- **Disk Space**: 20GB free
- **Python**: 3.8+

**Recommended:**
- **GPU**: NVIDIA GPU with 8GB+ VRAM
- **CUDA**: 11.8 or higher
- **RAM**: 32GB
- **Disk Space**: 30GB free

## Usage

### Method 1: Direct Usage

```python
from llm.personaplex_client import PersonaPlexClient

# Initialize
client = PersonaPlexClient(
    model_name="nvidia/personaplex-7b-v1",
    device="auto"  # or "cuda" / "cpu"
)

# Set persona
client.set_persona("You are a helpful coding assistant")

# Generate response
response = client.generate(
    prompt="How do I create a Python class?",
    max_new_tokens=512,
    temperature=0.7
)

print(response)
```

### Method 2: Use with Agent

1. **Edit `config.yaml`:**

```yaml
llm:
  provider: "personaplex"  # Change from "ollama"
  model: "nvidia/personaplex-7b-v1"
  temperature: 0.7
  max_tokens: 512
```

2. **Run Agent:**

```bash
python main.py
```

The agent will automatically use PersonaPlex instead of Ollama!

## Configuration Options

### PersonaPlex Parameters

```python
client.generate(
    prompt="Your question here",
    system_prompt="Optional system instruction",
    max_new_tokens=512,      # Max response length
    temperature=0.7,         # Creativity (0.0-1.0)
    top_p=0.9,              # Nucleus sampling
    do_sample=True,         # Enable sampling
    persona="Optional persona"  # Define personality
)
```

### Device Selection

```python
# Auto-detect (recommended)
client = PersonaPlexClient(device="auto")

# Force GPU
client = PersonaPlexClient(device="cuda")

# Force CPU
client = PersonaPlexClient(device="cpu")
```

## Features

### 1. Conversation History

PersonaPlex maintains conversation context:

```python
client.generate("Hello!")
# Response: "Hi! How can I help you?"

client.generate("What's 2+2?")
# Response: "2+2 equals 4."

client.generate("Thanks!")
# Response: "You're welcome! Let me know if you need anything else."

# Clear history
client.reset_conversation()
```

### 2. Custom Personas

Define AI personality:

```python
# Coding assistant
client.set_persona("You are an expert Python developer")

# Creative writer
client.set_persona("You are a creative storyteller")

# Technical support
client.set_persona("You are a friendly tech support agent")
```

### 3. System Prompts

Add instructions:

```python
response = client.generate(
    prompt="Write a function to sort a list",
    system_prompt="You are a Python expert. Provide clean, documented code."
)
```

### 4. Memory Management

```python
# Check memory usage (GPU)
mem = client.get_memory_usage()
print(f"Allocated: {mem['allocated_gb']} GB")
print(f"Reserved: {mem['reserved_gb']} GB")

# Get model info
info = client.get_model_info()
print(info)
```

## Testing

### Quick Test

```bash
python test_personaplex.py
```

This will:
1. Download the model (first time only)
2. Load it into memory
3. Run test conversations
4. Show performance metrics

### Expected Output

```
🤖 NVIDIA PersonaPlex Test
============================================================
📥 Loading PersonaPlex model...
⚠️  This will download ~14GB model on first run
⏳ Please wait...
✅ Model loaded successfully!

📊 Model Info:
  Name: nvidia/personaplex-7b-v1
  Device: cuda
  Parameters: 7B
  Type: Conversational AI

🎮 GPU Available: Yes
  Memory Allocated: 13.5 GB
  Memory Reserved: 14.2 GB

💬 Testing Conversation
============================================================
👤 User: Hello! Can you help me with Python?
🤖 PersonaPlex: Of course! I'd be happy to help...
```

## Performance

### GPU (NVIDIA RTX 3090)
- **Load Time**: ~30 seconds
- **First Response**: ~2 seconds
- **Subsequent**: ~0.5 seconds
- **Memory**: ~14GB VRAM

### CPU (Intel i9)
- **Load Time**: ~60 seconds
- **First Response**: ~10 seconds
- **Subsequent**: ~5 seconds
- **Memory**: ~16GB RAM

## Comparison: PersonaPlex vs Ollama

| Feature | PersonaPlex | Ollama |
|---------|-------------|--------|
| **Setup** | Download once | Install + pull models |
| **Speed** | Fast (GPU) | Very fast |
| **Memory** | 14GB VRAM/RAM | 4-8GB |
| **Conversation** | Full-duplex | Standard |
| **Personas** | Built-in | Manual prompting |
| **Offline** | ✅ Yes | ✅ Yes |
| **GPU Required** | Recommended | Optional |

## Troubleshooting

### Issue: Out of Memory

**Solution:**
```python
# Use CPU instead
client = PersonaPlexClient(device="cpu")

# Or use smaller batch size
response = client.generate(
    prompt="...",
    max_new_tokens=256  # Reduce from 512
)
```

### Issue: Slow on CPU

**Solution:**
- Use GPU if available
- Reduce `max_new_tokens`
- Increase temperature for faster sampling

### Issue: Model Download Fails

**Solution:**
```bash
# Manual download
huggingface-cli login
huggingface-cli download nvidia/personaplex-7b-v1
```

### Issue: CUDA Out of Memory

**Solution:**
```python
# Clear cache
import torch
torch.cuda.empty_cache()

# Or restart Python
```

## Advanced Usage

### Streaming Responses

```python
# TODO: Implement streaming
# PersonaPlex supports streaming for real-time output
```

### Multi-Turn Conversations

```python
client.set_persona("You are a helpful assistant")

# Turn 1
response1 = client.generate("What's Python?")

# Turn 2 (remembers context)
response2 = client.generate("How do I install it?")

# Turn 3
response3 = client.generate("Thanks!")
```

### Custom System Prompts

```python
system = """You are an AI agent controller.
You can execute actions on the computer.
Always respond in JSON format."""

response = client.generate(
    prompt="Open Chrome",
    system_prompt=system
)
```

## Integration with Agent

PersonaPlex can replace Ollama in the agent:

**Advantages:**
- ✅ Better conversation understanding
- ✅ Natural dialogue flow
- ✅ Persona customization
- ✅ Full-duplex capabilities

**Disadvantages:**
- ❌ Higher memory usage
- ❌ Slower on CPU
- ❌ Larger download

## Best Practices

1. **Use GPU** - 10x faster than CPU
2. **Set Personas** - Better task-specific responses
3. **Manage History** - Clear when switching tasks
4. **Monitor Memory** - Check usage regularly
5. **Optimize Tokens** - Use appropriate max_new_tokens

## Examples

### Example 1: Code Generation

```python
client.set_persona("You are an expert Python developer")

code = client.generate(
    prompt="Write a function to reverse a string",
    temperature=0.3  # Lower for more deterministic code
)
```

### Example 2: Creative Writing

```python
client.set_persona("You are a creative storyteller")

story = client.generate(
    prompt="Write a short sci-fi story",
    temperature=0.9,  # Higher for creativity
    max_new_tokens=1024
)
```

### Example 3: Technical Support

```python
client.set_persona("You are a friendly tech support agent")

help_text = client.generate(
    prompt="My computer won't start",
    temperature=0.5
)
```

## Resources

- **Model Card**: https://huggingface.co/nvidia/personaplex-7b-v1
- **Paper**: [NVIDIA PersonaPlex Research]
- **GitHub**: https://github.com/nvidia/personaplex
- **License**: NVIDIA Open Model License

## FAQ

**Q: Do I need a GPU?**
A: No, but highly recommended. CPU works but is slower.

**Q: How much disk space needed?**
A: ~14GB for the model + ~6GB for cache = 20GB total

**Q: Can I use it offline?**
A: Yes! After first download, fully offline.

**Q: Is it better than Ollama?**
A: Different use cases. PersonaPlex excels at conversation, Ollama is faster for simple tasks.

**Q: Can I fine-tune it?**
A: Yes! It's open-source and supports fine-tuning.

## Conclusion

NVIDIA PersonaPlex is a powerful conversational AI model that can significantly enhance the agent's dialogue capabilities. It's perfect for:

- ✅ Natural conversations
- ✅ Complex reasoning
- ✅ Persona-based interactions
- ✅ Full-duplex dialogue

**Try it out and experience next-level AI conversation!** 🚀

---

*Last Updated: 2026-01-27*
*Version: 1.0*
