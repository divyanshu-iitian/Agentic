"""
Vision Client (Local Eyes) 👁️

Uses local Vision Language Models (like Llava) via Ollama to "see" the screen.
Responsible for finding UI elements when DOM/Accessibility fails.
"""

import requests
import json
import base64
from typing import Optional, Tuple, Dict
from core.config import get_config
from utils.logger import log

class VisionClient:
    def __init__(self, model_name: str = "llava"):
        self.base_url = "http://localhost:11434/api/generate"
        self.model = model_name
        self.config = get_config()
        
    def detect_element(self, image_path: str, element_description: str) -> Optional[Tuple[int, int]]:
        """
        Ask the Vision Model to find an element.
        Returns (x, y) coordinates or None.
        """
        prompt = f"""
        Look at this screenshot. Find the center coordinates of the '{element_description}'.
        
        IMPORTANT:
        - Output ONLY a JSON object: {{"x": 123, "y": 456}}
        - The image size is standard 1920x1080 (or as observed).
        - If not found, output {{"error": "not found"}}
        """
        
        try:
            with open(image_path, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode("utf-8")
                
            payload = {
                "model": self.model,
                "prompt": prompt,
                "images": [image_b64],
                "stream": False,
                "format": "json" # Force JSON mode if supported
            }
            
            response = requests.post(self.base_url, json=payload, timeout=30)
            if response.status_code != 200:
                log.error(f"Vision API Error: {response.text}")
                return None
                
            result_text = response.json().get("response", "")
            data = json.loads(result_text)
            
            if "x" in data and "y" in data:
                return (int(data["x"]), int(data["y"]))
            
            return None
            
        except Exception as e:
            log.error(f"Vision Detection Failed: {e}")
            return None
