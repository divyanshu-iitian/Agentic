"""
Vision Analyzer

Uses llava vision model to analyze camera frames and answer visual queries.
Special feature: Recognizes Divyanshu (boy in black t-shirt).
"""

import base64
import io
from typing import Optional, Dict, Any
from PIL import Image
import requests
from utils.logger import log


class VisionAnalyzer:
    """
    Vision analysis using llava model.
    
    Features:
    - Analyze camera frames
    - Answer visual questions
    - Person recognition (Divyanshu detection)
    """
    
    def __init__(self, model: str = "llava:latest", base_url: str = "http://localhost:11434"):
        """
        Initialize vision analyzer.
        
        Args:
            model: llava model name
            base_url: Ollama API endpoint
        """
        self.model = model
        self.base_url = base_url
        self.api_url = f"{base_url}/api/generate"
        
        log.info(f"Vision analyzer initialized: {model}")
    
    def _encode_image(self, image: Image.Image) -> str:
        """
        Encode PIL Image to base64.
        
        Args:
            image: PIL Image
        
        Returns:
            Base64 encoded string
        """
        # Convert to RGB if needed
        if image.mode != "RGB":
            image = image.convert("RGB")
        
        # Resize if too large (llava works better with smaller images)
        max_size = 1024
        if max(image.size) > max_size:
            ratio = max_size / max(image.size)
            new_size = tuple(int(dim * ratio) for dim in image.size)
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        # Encode to base64
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        img_bytes = buffer.getvalue()
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')
        
        return img_base64
    
    def analyze_frame(self, image: Image.Image, query: str = "Describe what you see in detail.") -> str:
        """
        Analyze camera frame with vision model.
        
        Args:
            image: PIL Image from camera
            query: Question to ask about the image
        
        Returns:
            Analysis result
        """
        try:
            # Encode image
            img_base64 = self._encode_image(image)
            
            # Build prompt with Divyanshu detection
            enhanced_query = f"""{query}

IMPORTANT RECOGNITION RULES:
- If you see a boy or man wearing a black t-shirt, that person is DIVYANSHU
- Be specific about clothing colors and details
- Mention if you see any person and what they're wearing
- If it's a boy in black t-shirt, say: "This is Divyanshu" or "I can see Divyanshu"
"""
            
            # Call Ollama vision API
            payload = {
                "model": self.model,
                "prompt": enhanced_query,
                "images": [img_base64],
                "stream": False
            }
            
            log.info(f"📸 Analyzing frame with query: {query[:50]}...")
            
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=60.0  # Vision models are slower
            )
            
            if response.status_code != 200:
                log.error(f"Vision API error: {response.status_code}")
                return f"Error: Failed to analyze image (status {response.status_code})"
            
            result = response.json()
            analysis = result.get("response", "")
            
            # Post-process: Ensure Divyanshu is mentioned if black t-shirt detected
            if "black" in analysis.lower() and ("shirt" in analysis.lower() or "t-shirt" in analysis.lower()):
                if "boy" in analysis.lower() or "man" in analysis.lower() or "person" in analysis.lower():
                    if "divyanshu" not in analysis.lower():
                        # Force add Divyanshu mention
                        analysis = f"I can see Divyanshu (wearing a black t-shirt). {analysis}"
            
            log.info(f"✅ Vision analysis complete: {analysis[:100]}...")
            return analysis
        
        except requests.Timeout:
            log.error("Vision analysis timeout")
            return "Error: Vision analysis timed out (llava model too slow)"
        
        except Exception as e:
            log.error(f"Vision analysis failed: {e}")
            return f"Error: {str(e)}"
    
    def answer_visual_question(self, image: Image.Image, question: str) -> str:
        """
        Answer a specific question about the image.
        
        Args:
            image: PIL Image
            question: User's question
        
        Returns:
            Answer
        """
        # Customize query based on question type
        if any(word in question.lower() for word in ["who", "person", "people", "someone"]):
            query = f"{question}\n\nIMPORTANT: If you see a boy/man in a black t-shirt, that's DIVYANSHU."
        else:
            query = question
        
        return self.analyze_frame(image, query)
    
    def detect_person(self, image: Image.Image) -> Dict[str, Any]:
        """
        Detect if person is present and identify them.
        
        Args:
            image: PIL Image
        
        Returns:
            Detection result with person info
        """
        query = """Is there a person in this image? If yes, describe:
1. What they're wearing (especially t-shirt color)
2. Their approximate age and gender
3. What they're doing

CRITICAL: If it's a boy/man wearing a BLACK t-shirt, that person is DIVYANSHU."""
        
        analysis = self.analyze_frame(image, query)
        
        # Parse result
        person_detected = any(word in analysis.lower() for word in ["person", "boy", "man", "girl", "woman", "people"])
        is_divyanshu = "divyanshu" in analysis.lower()
        
        return {
            "person_detected": person_detected,
            "is_divyanshu": is_divyanshu,
            "description": analysis
        }


# Global vision analyzer instance
_analyzer = None


def get_vision_analyzer() -> VisionAnalyzer:
    """Get or create global vision analyzer."""
    global _analyzer
    if _analyzer is None:
        _analyzer = VisionAnalyzer()
    return _analyzer
