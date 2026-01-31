"""
NVIDIA PersonaPlex Integration

PersonaPlex is NVIDIA's open-source conversational AI model.
- 7B parameters
- Full-duplex dialogue (listen + speak simultaneously)
- Natural turn-taking and interruption handling
- Customizable personas
- Low latency real-time conversation

Model: nvidia/personaplex-7b-v1
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from typing import Optional, Dict, Any
from utils.logger import log
import os


class PersonaPlexClient:
    """Client for NVIDIA PersonaPlex conversational AI"""
    
    def __init__(self, model_name: str = "nvidia/personaplex-7b-v1", device: str = "auto"):
        """
        Initialize PersonaPlex model.
        
        Args:
            model_name: HuggingFace model identifier
            device: Device to run on ('cuda', 'cpu', or 'auto')
        """
        self.model_name = model_name
        
        # Auto-detect device
        if device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        
        log.info(f"🤖 Loading PersonaPlex model: {model_name}")
        log.info(f"📍 Device: {self.device}")
        
        # Load tokenizer
        try:
            # Get HuggingFace token from environment
            hf_token = os.getenv("HF_TOKEN")
            
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                trust_remote_code=True,
                token=hf_token  # Use token for gated models
            )
            log.info("✅ Tokenizer loaded")
        except Exception as e:
            log.error(f"Failed to load tokenizer: {e}")
            raise
        
        # Load model
        try:
            hf_token = os.getenv("HF_TOKEN")
            
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map=self.device,
                trust_remote_code=True,
                low_cpu_mem_usage=True,
                token=hf_token  # Use token for gated models
            )
            log.info("✅ Model loaded successfully")
        except Exception as e:
            log.error(f"Failed to load model: {e}")
            raise
        
        # Set to evaluation mode
        self.model.eval()
        
        # Conversation history
        self.conversation_history = []
        
        log.info("🎉 PersonaPlex initialized and ready!")
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_new_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        do_sample: bool = True,
        persona: Optional[str] = None
    ) -> str:
        """
        Generate response using PersonaPlex.
        
        Args:
            prompt: User input
            system_prompt: System instruction
            max_new_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            do_sample: Whether to use sampling
            persona: Optional persona definition
            
        Returns:
            Generated response
        """
        # Build conversation context
        messages = []
        
        # Add system prompt
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Add persona if specified
        if persona:
            messages.append({"role": "system", "content": f"Persona: {persona}"})
        
        # Add conversation history
        messages.extend(self.conversation_history[-10:])  # Keep last 10 turns
        
        # Add current user message
        messages.append({"role": "user", "content": prompt})
        
        # Format prompt
        formatted_prompt = self._format_messages(messages)
        
        # Tokenize
        inputs = self.tokenizer(
            formatted_prompt,
            return_tensors="pt",
            truncation=True,
            max_length=2048
        ).to(self.device)
        
        # Generate
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=do_sample,
                pad_token_id=self.tokenizer.eos_token_id
            )
        
        # Decode
        response = self.tokenizer.decode(
            outputs[0][inputs['input_ids'].shape[1]:],
            skip_special_tokens=True
        ).strip()
        
        # Update conversation history
        self.conversation_history.append({"role": "user", "content": prompt})
        self.conversation_history.append({"role": "assistant", "content": response})
        
        return response
    
    def _format_messages(self, messages: list) -> str:
        """Format messages for PersonaPlex"""
        formatted = ""
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            if role == "system":
                formatted += f"System: {content}\n"
            elif role == "user":
                formatted += f"User: {content}\n"
            elif role == "assistant":
                formatted += f"Assistant: {content}\n"
        
        formatted += "Assistant:"
        return formatted
    
    def reset_conversation(self):
        """Clear conversation history"""
        self.conversation_history = []
        log.info("🔄 Conversation history cleared")
    
    def set_persona(self, persona: str):
        """
        Set a persona for the conversation.
        
        Args:
            persona: Persona description (e.g., "helpful coding assistant")
        """
        self.conversation_history.insert(0, {
            "role": "system",
            "content": f"Persona: {persona}"
        })
        log.info(f"🎭 Persona set: {persona}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            "model_name": self.model_name,
            "device": self.device,
            "parameters": "7B",
            "type": "Conversational AI",
            "features": [
                "Full-duplex dialogue",
                "Natural turn-taking",
                "Interruption handling",
                "Customizable personas",
                "Low latency"
            ]
        }
    
    def check_gpu_available(self) -> bool:
        """Check if GPU is available"""
        return torch.cuda.is_available()
    
    def get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage"""
        if self.device == "cuda":
            allocated = torch.cuda.memory_allocated() / 1024**3  # GB
            reserved = torch.cuda.memory_reserved() / 1024**3    # GB
            return {
                "allocated_gb": round(allocated, 2),
                "reserved_gb": round(reserved, 2)
            }
        return {"allocated_gb": 0, "reserved_gb": 0}


# Convenience function
def create_personaplex_client(
    model_name: str = "nvidia/personaplex-7b-v1",
    device: str = "auto"
) -> PersonaPlexClient:
    """
    Create and return a PersonaPlex client.
    
    Args:
        model_name: Model identifier
        device: Device to use
        
    Returns:
        Initialized PersonaPlexClient
    """
    return PersonaPlexClient(model_name=model_name, device=device)
