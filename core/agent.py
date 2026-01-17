"""
Main Agent Orchestration
Core agent loop: Plan -> Execute -> Verify (Refactored for Agent 2.0)
"""

import asyncio
from typing import Optional
from core.config import get_config
from core.state import TaskState

from llm.ollama_client import OllamaClient
from llm.prompt import AGENT_SYSTEM_PROMPT_WITH_EXAMPLES, build_user_prompt
from llm.parser import JSONParser
from execution.actions import parse_action
from execution.desktop_executor import DesktopExecutor
from execution.browser_executor import BrowserExecutor
from planning.action_validator import ActionValidator
from observation.screen_capture import ScreenCapture
from safety.kill_switch import KillSwitch, ActionLimiter

# 🧠 NEW: Perception & Interaction layers
from perception.screen_observer import ScreenObserver
from perception.ocr_extractor import OCRExtractor
from perception.ui_state_builder import UIStateBuilder
from perception.change_detector import ChangeDetector
from interaction.keyboard_policy import KeyboardPolicy
from interaction.text_anchor_clicker import TextAnchorClicker
from interaction.icon_fallback import IconFallback

# 🧠 AGENT 2.0 COMPONENTS
from core.planner import Planner
from core.critic import Critic
from core.world_model import WorldModel

# 🧠 NEW: Vision
from perception.vision_client import VisionClient

from utils.logger import log


class Agent:
    """Main autonomous agent with Planner-Executor-Critic architecture"""
    
    def __init__(self):
        self.config = get_config()
        
        # Initialize components
        self.state = TaskState()
        self.llm = OllamaClient()
        self.parser = JSONParser()
        self.validator = ActionValidator()
        self.limiter = ActionLimiter()
        
        # 🧠 NEW: Vision Layer
        self.vision_client = VisionClient() # Uses Ollama (Llava)
        
        # Executors
        self.desktop_executor = DesktopExecutor(vision_client=self.vision_client)
        self.browser_executor = BrowserExecutor()
        
        # Perception layer
        self.screen_observer = ScreenObserver(save_observations=True)
        self.ocr_extractor = OCRExtractor(min_confidence=30.0)
        self.ui_state_builder = UIStateBuilder()
        self.change_detector = ChangeDetector()
        
        # AGENT 2.0 BRAIN 🧠
        self.world_model = WorldModel()
        self.planner = Planner(self.llm, self.world_model)
        self.critic = Critic(self.llm)
        
        # Perception state
        self.current_ui_state = None
        self.last_ui_state = None
        self.last_observation = None
        
        # Safety
        self.kill_switch = KillSwitch(callback=self.emergency_stop)
        
        self.running = False
        
        log.info("🤖 Agent 2.0 initialized (Planner-Executor-Critic)")
    
    def start(self):
        """Start the agent"""
        self.kill_switch.activate()
        self.running = True
        log.info("🟢 Agent started")
    
    def stop(self):
        """Stop the agent"""
        self.running = False
        self.kill_switch.deactivate()
        log.info("🔴 Agent stopped")
    
    def emergency_stop(self):
        """Emergency stop callback"""
        log.critical("⚠️ EMERGENCY STOP")
        self.stop()
        asyncio.create_task(self.browser_executor.cleanup())
    
    async def execute_task(self, task: str) -> bool:
        """
        Execute a task using Agent 2.0 Architecture.
        Flow: Plan -> Loop [Execute Step -> Verify] -> Done
        """
        log.info(f"📋 New task: {task}")
        
        self.state.start_task(task)
        self.world_model.clear_task_state()
        self.limiter.reset()
        
        # PHASE 1: PLANNING 🗺️
        log.info("🤔 Planning...")
        steps = self.planner.create_plan(task)
        if not steps:
            log.error("Failed to create plan")
            return False
            
        # PHASE 2: EXECUTION LOOP 🔄
        try:
            while self.running and not self.planner.is_done():
                current_step = self.planner.get_next_step()
                log.info(f"👉 Current Step: {current_step}")
                
                step_success = False
                attempts = 0
                max_attempts = 3
                
                while not step_success and attempts < max_attempts:
                    attempts += 1
                    
                    if not self.limiter.increment():
                        log.error("Action limit exceeded")
                        return False
                        
                    # 1. OBSERVE
                    observation = await self._observe()
                    self.state.update_observation(observation)
                    
                    # 2. EXECUTE (Reasoning for single step)
                    action_json = self._reason(current_step, observation, task_context=task)
                    
                    if not action_json:
                        log.error("Failed to decide action")
                        break
                        
                    # Validate & Execute (standard logic)
                    action_name = action_json["action"]
                    action_args = action_json.get("args", {})
                    
                    # Prevent loops (legacy check, still useful)
                    if not self.state.track_action(action_name, action_args):
                         log.warning("Loop detected in micro-steps, forcing verification")
                         break # Break loop to force verification/replanning

                    # Check app spamming
                    if action_name == "open_app" or (action_name == "press_key" and action_args.get("key") == "win"):
                         app = action_args.get("name", "start menu")
                         if self.world_model.state.active_app == app: # Use WorldModel for context
                             log.info(f"Skipping {app}, already active")
                             continue

                    # Execute
                    result = await self._execute(action_name, action_args)
                    self.world_model.record_action(action_name, action_args, result)
                    
                    if action_name == "stop":
                         log.info("Agent decided to stop early")
                         break
                         
                    # 3. VERIFY (Critic) 🕵️
                    # We verify after every action? Or after the LLM thinks it's done with the step?
                    # For now, let's verify after every action to see if the step is complete.
                    new_observation = await self._observe()
                    
                    success, reason = self.critic.verify(current_step, new_observation)
                    
                    if success:
                        log.info(f"✅ Step Verified: {current_step}")
                        step_success = True
                        self.planner.mark_step_complete()
                    else:
                        log.info(f"❌ Step Not Yet Complete: {reason}")
                        # If action failed explicitly, maybe wait a bit
                        if not result.get("success"):
                            await asyncio.sleep(1)
                            
                if not step_success:
                    log.error(f"Failed step '{current_step}' after {max_attempts} attempts. Aborting.")
                    self.state.complete_task(success=False)
                    return False
            
            log.info("🎉 Task Completed Successfully!")
            self.state.complete_task(success=True)
            return True
            
        except Exception as e:
            log.error(f"Task execution failed: {e}")
            self.state.complete_task(success=False)
            return False
    
    async def _observe(self) -> str:
        """Gather observation"""
        # (Simplified for brevity - reusing existing logic but writing it out cleanly)
        screen_obs = self.screen_observer.observe()
        text_elements = self.ocr_extractor.extract(screen_obs.image)
        self.current_ui_state = self.ui_state_builder.build_state(text_elements)
        
        obs_text = f"UI STATE:\n{self.current_ui_state}\n"
        if text_elements:
             obs_text += f"\nVISIBLE TEXT: {self.ocr_extractor.get_text_summary(text_elements)}\n"
        
        if self.browser_executor.page:
             obs_text += f"\nBROWSER: {await self.browser_executor.get_dom_summary()}"
             
        return obs_text
    
    def _reason(self, step: str, observation: str, task_context: str) -> Optional[dict]:
        """Reason about a SINGLE step within the plan"""
        # Focus the prompt on the current step
        prompt = f"""OVERALL GOAL: {task_context}
CURRENT SUB-TASK: {step}

OBSERVATION:
{observation}

What is the next action to achieve the SUB-TASK?"""
        
        try:
            response = self.llm.generate(prompt, system_prompt=AGENT_SYSTEM_PROMPT_WITH_EXAMPLES)
            return self.parser.parse_llm_output(response)
        except Exception as e:
            log.error(f"Reasoning failed: {e}")
            return None

    async def _execute(self, action: str, args: dict) -> dict:
        """Execute action (Legacy wrapper)"""
        # Browser actions
        if action.startswith("browser_"):
            return await self.browser_executor.execute(action, args)
        
        # Desktop actions
        else:
            try:
                result = self.desktop_executor.execute(action, args)
                if not result.get("success"):
                     log.warning(f"Action failed: {result.get('error')}")
                     await asyncio.sleep(1) 
                return result
            except Exception as e:
                log.error(f"Execution failed: {e}")
                return {"success": False, "error": str(e)}
