"""
Planner - High-Level Strategy Engine 🗺️

Responsible for decomposing complex user requests into atomic, verifiable steps.
Does NOT execute actions. ONLY PLANS.
"""

from typing import List, Dict, Optional
from llm.ollama_client import OllamaClient
from llm.gemini_client import GeminiClient
from core.world_model import WorldModel
from utils.logger import log
import json

SYSTEM_PROMPT_PLANNER = """
You are the PLANNER for an autonomous desktop agent.
Your job is to break down a User Task into a linear list of logical steps.

OUTPUT FORMAT:
JSON list of strings. Do not include markdown.

EXAMPLE:
Task: "Search for VLC on Start Menu and open it"
Response:
[
  "Open Start Menu",
  "Type 'VLC'",
  "Wait for search results",
  "Press Enter to open",
  "Verify VLC is open"
]

RULES:
1. Keep steps atomic (one action per step).
2. EXCEPTION: For launching apps, use a SINGLE step: "Launch App 'Name'". DO NOT break it into "Open Menu" -> "Type".
3. Include "Verify" steps to check if actions succeeded.
4. Be explicit.
"""

class Planner:
    def __init__(self, llm: OllamaClient, world_model: WorldModel):
        self.local_llm = llm
        self.cloud_llm = GeminiClient()
        self.world_model = world_model
        self.current_plan: List[str] = []
        self.current_step_index: int = 0
        
    def create_plan(self, task: str) -> List[str]:
        """Generate a high-level plan for the task"""
        prompt = f"TASK: {task}\n\nBreak this down into steps:"
        
        # Try Cloud Brain (Gemini) First ☁️
        response = None
        if self.cloud_llm.api_key:
            log.info("☁️ Using Gemini Pro for Planning...")
            response = self.cloud_llm.generate(prompt, system_prompt=SYSTEM_PROMPT_PLANNER)
            
        # Fallback to Local Brain (Ollama) 🏠
        if not response:
            log.info("🏠 Using Local Ollama for Planning...")
            try:
                response = self.local_llm.generate(prompt, system_prompt=SYSTEM_PROMPT_PLANNER)
            except Exception as e:
                log.error(f"Planning failed: {e}")
                return [task]

        try:
            # Try to parse JSON from response
            # Simple heuristic cleaning if LLM adds text around JSON
            clean_response = response.strip()
            if "```json" in clean_response:
                clean_response = clean_response.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_response:
                clean_response = clean_response.split("```")[1].split("```")[0].strip()
                
            steps = json.loads(clean_response)
            if isinstance(steps, list):
                self.current_plan = steps
                self.current_step_index = 0
                log.info(f"📝 Created plan with {len(steps)} steps: {steps}")
                return steps
            else:
                log.error(f"Planner output not a list: {response}")
                return [task] # Fallback: Treat whole task as one step
                
        except Exception as e:
            log.error(f"Planning failed: {e}")
            return [task] # Fallback
            
    def get_next_step(self) -> Optional[str]:
        """Get the current step description"""
        if self.current_step_index < len(self.current_plan):
            return self.current_plan[self.current_step_index]
        return None
        
    def mark_step_complete(self):
        """Advance to next step"""
        self.current_step_index += 1
        
    def is_done(self) -> bool:
        """Check if plan is finished"""
        return self.current_step_index >= len(self.current_plan)
