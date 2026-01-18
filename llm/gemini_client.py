"""
Gemini API Client ☁️

Handles communication with Google's Gemini API for high-level planning.
Uses direct REST API to minimize dependencies.
"""

import os
import requests
import json
from typing import Optional
from dotenv import load_dotenv
from utils.logger import log

load_dotenv()

class GeminiClient:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        # Updated to gemini-2.0-flash as requested
        self.output_model = "gemini-2.0-flash"
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.output_model}:generateContent?key={self.api_key}"
        
        if not self.api_key:
            log.warning("GEMINI_API_KEY not found in environment variables") # The instruction provided a truncated message. I've completed it to maintain syntactic correctness.
            
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """
        Generate text using Gemini.
        """
        if not self.api_key:
            raise ValueError("Gemini API Key not configured")
            
        headers = {
            "Content-Type": "application/json"
        }
        
        # Construct payload with system prompt if possible, or merge it
        full_text = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        
        payload = {
            "contents": [{
                "parts": [{"text": full_text}]
            }],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 2048
            }
        }
        
        # Use simple URL as defined in init
        url = self.url
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if "candidates" in data and data["candidates"]:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            else:
                log.error(f"Gemini Empty Response: {data}")
                return ""
                
        except Exception as e:
            log.error(f"Gemini API Error: {e}")
            return "" # Return empty string on failure to allow fallback
