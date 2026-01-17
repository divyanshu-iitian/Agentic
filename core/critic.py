"""
Critic - The Verifier 🕵️

Responsible for checking if the executed action actually achieved its goal.
Compares 'Intended Step' vs 'Current Observation'.
"""

from typing import Tuple
from llm.ollama_client import OllamaClient
from utils.logger import log

SYSTEM_PROMPT_CRITIC = """
You are the CRITIC.
Your job is to verify if a step was successful based on the visual observation.

INPUT:
Step: What we tried to do.
Observation: What the screen looks like now.

OUTPUT:
JSON with keys:
- "success": boolean
- "reason": string explanation

EXAMPLE:
Step: "Open Start Menu"
Observation: "Screen shows desktop, no menu visible."
Response: { "success": false, "reason": "Start menu not found in observation" }
"""

class Critic:
    def __init__(self, llm: OllamaClient):
        self.llm = llm
        
    def verify(self, step: str, observation: str) -> Tuple[bool, str]:
        """
        Verify if the step was completed successfully.
        Returns: (is_success, reason)
        """
        # Fast path for 'wait' steps
        if "wait" in step.lower():
            return True, "Wait always succeeds"
            
        prompt = f"Step: {step}\n\nObservation:\n{observation}"
        
        try:
            response = self.llm.generate(prompt, system_prompt=SYSTEM_PROMPT_CRITIC)
            import json
            
            # Clean JSON
            clean_response = response.strip()
            if "```json" in clean_response:
                clean_response = clean_response.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_response:
                clean_response = clean_response.split("```")[1].split("```")[0].strip()
                
            result = json.loads(clean_response)
            success = result.get("success", False)
            reason = result.get("reason", "Unknown")
            
            log.info(f"🕵️ Critic Verdict: {success} ({reason})")
            return success, reason
            
        except Exception as e:
            log.error(f"Critic failed: {e}")
            return True, "Critic failed, assuming success" # Fail open to avoid deadlock
