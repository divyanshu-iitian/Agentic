"""
NVIDIA PersonaPlex - Optimized for 8GB VRAM

This version uses quantization and optimizations to run on 8GB VRAM.
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from typing import Optional, Dict, Any
from utils.logger import log


class PersonaPlexClientOptimized:
    """Optimized PersonaPlex client for 8GB VRAM"""
    
    def __init__(
        self,
        model_name: str = "nvidia/personaplex-7b-v1",
        device: str = "auto",
        use_8bit: bool = True  # 8-bit quantization for lower memory
    ):
        """
        Initialize optimized PersonaPlex.
        
        Args:
            model_name: Model identifier
            device: Device to use
            use_8bit: Use 8-bit quantization (recommended for 8GB VRAM)
        """
        self.model_name = model_name
        self.use_8bit = use_8bit
        
        # Auto-detect device
        if device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        
        log.info(f"🤖 Loading PersonaPlex (Optimized for 8GB VRAM)")
        log.info(f"📍 Device: {self.device}")
        log.info(f"🔧 8-bit Quantization: {use_8bit}")
        
        # Load tokenizer
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                trust_remote_code=True
            )
            log.info("✅ Tokenizer loaded")
        except Exception as e:
            log.error(f"Failed to load tokenizer: {e}")
            raise
        
        # Load model with optimizations
        try:
            if self.device == "cuda" and use_8bit:
                # 8-bit quantization config
                quantization_config = BitsAndBytesConfig(
                    load_in_8bit=True,
                    llm_int8_threshold=6.0,
                    llm_int8_has_fp16_weight=False
                )
                
                log.info("🔧 Using 8-bit quantization (saves ~50% VRAM)")
                
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    quantization_config=quantization_config,
                    device_map="auto",
                    trust_remote_code=True,
                    low_cpu_mem_usage=True
                )
            else:
                # Standard loading
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                    device_map=self.device,
                    trust_remote_code=True,
                    low_cpu_mem_usage=True
                )
            
            log.info("✅ Model loaded successfully")
            
            # Show memory usage
            if self.device == "cuda":
                mem = self.get_memory_usage()
                log.info(f"💾 VRAM Usage: {mem['allocated_gb']} GB / {mem['total_gb']} GB")
                
                if mem['allocated_gb'] > 7.5:
                    log.warning("⚠️  High VRAM usage! Consider using 8-bit mode.")
                else:
                    log.info("✅ VRAM usage is acceptable")
                    
        except Exception as e:
            log.error(f"Failed to load model: {e}")
            raise
        
        # Set to evaluation mode
        self.model.eval()
        
        # Conversation history
        self.conversation_history = []
        
        log.info("🎉 PersonaPlex (Optimized) ready!")
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_new_tokens: int = 256,  # Reduced default for 8GB
        temperature: float = 0.7,
        top_p: float = 0.9,
        do_sample: bool = True,
        persona: Optional[str] = None
    ) -> str:
        """
        Generate response (optimized for 8GB VRAM).
        
        Args:
            prompt: User input
            system_prompt: System instruction
            max_new_tokens: Max tokens (keep lower for 8GB)
            temperature: Sampling temperature
            top_p: Nucleus sampling
            do_sample: Use sampling
            persona: Optional persona
            
        Returns:
            Generated response
        """
        # Build messages
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        if persona:
            messages.append({"role": "system", "content": f"Persona: {persona}"})
        
        # Keep only last 5 turns to save memory
        messages.extend(self.conversation_history[-5:])
        messages.append({"role": "user", "content": prompt})
        
        # Format
        formatted_prompt = self._format_messages(messages)
        
        # Tokenize with truncation
        inputs = self.tokenizer(
            formatted_prompt,
            return_tensors="pt",
            truncation=True,
            max_length=1024  # Reduced for 8GB
        ).to(self.device)
        
        # Generate with memory optimization
        with torch.no_grad():
            # Clear cache before generation
            if self.device == "cuda":
                torch.cuda.empty_cache()
            
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=do_sample,
                pad_token_id=self.tokenizer.eos_token_id,
                use_cache=True  # Enable KV cache for speed
            )
        
        # Decode
        response = self.tokenizer.decode(
            outputs[0][inputs['input_ids'].shape[1]:],
            skip_special_tokens=True
        ).strip()
        
        # Update history (keep limited)
        self.conversation_history.append({"role": "user", "content": prompt})
        self.conversation_history.append({"role": "assistant", "content": response})
        
        # Keep only last 10 messages
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]
        
        return response
    
    def _format_messages(self, messages: list) -> str:
        """Format messages"""
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
        """Clear conversation history and free memory"""
        self.conversation_history = []
        if self.device == "cuda":
            torch.cuda.empty_cache()
        log.info("🔄 Conversation cleared, memory freed")
    
    def set_persona(self, persona: str):
        """Set persona"""
        self.conversation_history.insert(0, {
            "role": "system",
            "content": f"Persona: {persona}"
        })
        log.info(f"🎭 Persona set: {persona}")
    
    def get_memory_usage(self) -> Dict[str, float]:
        """Get VRAM usage"""
        if self.device == "cuda":
            allocated = torch.cuda.memory_allocated() / 1024**3
            reserved = torch.cuda.memory_reserved() / 1024**3
            total = torch.cuda.get_device_properties(0).total_memory / 1024**3
            
            return {
                "allocated_gb": round(allocated, 2),
                "reserved_gb": round(reserved, 2),
                "total_gb": round(total, 2),
                "free_gb": round(total - allocated, 2)
            }
        return {"allocated_gb": 0, "reserved_gb": 0, "total_gb": 0, "free_gb": 0}
    
    def optimize_memory(self):
        """Free up memory"""
        if self.device == "cuda":
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            log.info("🧹 Memory optimized")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model info"""
        return {
            "model_name": self.model_name,
            "device": self.device,
            "quantization": "8-bit" if self.use_8bit else "16-bit",
            "parameters": "7B",
            "optimized_for": "8GB VRAM",
            "features": [
                "8-bit quantization",
                "Memory optimization",
                "Limited context (1024 tokens)",
                "Reduced max tokens (256 default)"
            ]
        }


# Convenience function
def create_optimized_personaplex(
    model_name: str = "nvidia/personaplex-7b-v1",
    device: str = "auto",
    use_8bit: bool = True
) -> PersonaPlexClientOptimized:
    """
    Create optimized PersonaPlex for 8GB VRAM.
    
    Args:
        model_name: Model identifier
        device: Device
        use_8bit: Use 8-bit quantization
        
    Returns:
        Optimized client
    """
    return PersonaPlexClientOptimized(
        model_name=model_name,
        device=device,
        use_8bit=use_8bit
    )
