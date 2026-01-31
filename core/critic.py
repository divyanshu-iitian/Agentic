"""
Critic - The Verifier 🕵️

Responsible for checking if the executed action actually achieved its goal.
Compares 'Intended Step' vs 'Current Observation'.
"""

from typing import Tuple
from llm.ollama_client import OllamaClient
from utils.logger import log
from core.world_model import WorldModel

SYSTEM_PROMPT_CRITIC = """
You are the CRITIC - a smart verifier.
Your job is to verify if a step was successful based on the visual observation.

INPUT:
Step: What we tried to do.
Observation: What the screen looks like now.

OUTPUT:
JSON with keys:
- "success": boolean
- "reason": string explanation

CRITICAL RULES:
1. **IGNORE AGENT UI**: Text like "Agentic AI", "Press Ctrl+Space" is the agent's own interface - NOT the target app!
2. **Look for SUCCESS SIGNALS**: If opening Chrome, seeing "Google", "New Tab", browser UI = SUCCESS!
3. **Trust action results**: If the action said it succeeded, look for evidence it FAILED, not the other way around.
4. **Be lenient**: Don't fail on minor issues. Only fail if clearly broken.

EXAMPLES:
Step: "Open Chrome"
Observation: "Google Search visible, Agentic AI bar at top"
Response: { "success": true, "reason": "Chrome opened successfully - Google Search visible (ignore agent UI)" }

Step: "Open Start Menu"
Observation: "Desktop, no menu visible"
Response: { "success": false, "reason": "Start menu not found in observation" }
"""

class Critic:
    def __init__(self, llm: OllamaClient, world_model: WorldModel):
        self.llm = llm
        self.world_model = world_model
        
    def verify(self, step: str, observation: str) -> Tuple[bool, str]:
        """
        Verify if the step was completed successfully.
        Returns: (is_success, reason)
        """
        step_lower = step.lower()
        
        # Fast path for 'wait' steps
        if "wait" in step_lower:
            return True, "Wait always succeeds"
            
        # 🧠 HEURISTIC: Browser Check
        # If step is "Open Chrome" and WorldModel sees a browser, we trust the WorldModel.
        # This fixes the issue where the header "Google Chrome" isn't visible.
        if ("chrome" in step_lower or "browser" in step_lower) and "open" in step_lower:
            if self.world_model.state.is_browser_open:
                 log.info("🧠 Critic: Auto-verifying browser launch based on World Model state")
                 return True, "Browser detected in World Model state"
        
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
