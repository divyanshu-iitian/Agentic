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
from execution.os_executor import OSExecutor
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
from utils.window_manager import get_active_window_title


from core.memory import LongTermMemory

class Agent:
    """Main autonomous agent with Planner-Executor-Critic architecture"""
    
    def __init__(self):
        self.config = get_config()
        self.memory = LongTermMemory()
        
        # ... (rest of init) ...
        # Initialize components
        self.state = TaskState()
        
        # 🤖 LLM Client (Ollama or PersonaPlex)
        if self.config.llm.provider == "personaplex":
            # Check VRAM and choose appropriate version
            import torch
            if torch.cuda.is_available():
                vram_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
                log.info(f"🎮 Detected VRAM: {vram_gb:.1f} GB")
                
                if vram_gb < 12:
                    # Use optimized version for <12GB VRAM
                    from llm.personaplex_optimized import PersonaPlexClientOptimized
                    self.llm = PersonaPlexClientOptimized(
                        model_name=self.config.llm.model,
                        device="auto",
                        use_8bit=True  # 8-bit quantization
                    )
                    log.info("🤖 Using NVIDIA PersonaPlex (8-bit optimized)")
                else:
                    # Use standard version for >=12GB VRAM
                    from llm.personaplex_client import PersonaPlexClient
                    self.llm = PersonaPlexClient(
                        model_name=self.config.llm.model,
                        device="auto"
                    )
                    log.info("🤖 Using NVIDIA PersonaPlex (standard)")
            else:
                # CPU mode
                from llm.personaplex_client import PersonaPlexClient
                self.llm = PersonaPlexClient(
                    model_name=self.config.llm.model,
                    device="cpu"
                )
                log.info("🤖 Using NVIDIA PersonaPlex (CPU mode)")
        else:
            self.llm = OllamaClient()
            log.info("🤖 Using Ollama")
        
        self.parser = JSONParser()
        self.validator = ActionValidator()
        self.limiter = ActionLimiter()
        
        # 🧠 NEW: Vision Layer
        self.vision_client = VisionClient() # Uses Ollama (Llava)
        
        # 🧠 AGENT 2.0 BRAIN 🧠
        self.world_model = WorldModel()
        
        # Executors
        self.desktop_executor = DesktopExecutor(vision_client=self.vision_client, world_model=self.world_model)
        self.browser_executor = BrowserExecutor()
        self.os_executor = OSExecutor()  # 🚀 OS-Level Power!
        
        # Perception layer
        self.screen_observer = ScreenObserver(save_observations=True)
        self.ocr_extractor = OCRExtractor(min_confidence=30.0)
        self.ui_state_builder = UIStateBuilder()
        self.change_detector = ChangeDetector()
        
        self.planner = Planner(self.llm, self.world_model)
        self.critic = Critic(self.llm, self.world_model)
        
        # Perception state
        self.current_ui_state = None
        self.last_ui_state = None
        self.last_observation = None
        
        # Safety
        self.kill_switch = KillSwitch(callback=self.emergency_stop)
        
        self.running = False
        
        # 🎙️ Voice Narrator (Groq + Bark)
        try:
            from voice.voice_narrator import VoiceNarrator
            self.narrator = VoiceNarrator()
            self.voice_enabled = True
            log.info("🎙️ Voice Narrator (Groq + Bark) enabled")
        except Exception as e:
            log.warning(f"Voice Narrator not available: {e}")
            self.narrator = None
            self.voice_enabled = False
        
        log.info("🤖 Agent 2.0 initialized (Planner-Executor-Critic)")

    def learn_from_feedback(self, feedback: str):
        """Save feedback for the current/last task"""
        # Ideally we track current_task in self.state
        task = self.state.task if self.state.task else "General Feedback"
        steps = [str(e) for e in self.world_model.action_history] # Ensure strings
        
        self.memory.save_feedback(task, feedback, steps)
        log.info(f"🧠 Saved feedback for '{task}'")

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
        
        # 🎙️ Voice: Acknowledge task
        if self.voice_enabled:
            # We use an async wrapper or call in thread to not block the planning phase 
            # for the first acknowledgement, but for the rest it's sequential.
            import threading
            threading.Thread(target=self.narrator.say, args=(f"I'm starting the task: {task}",)).start()
        
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
                    
                    # 🧠 AGENT 2.0: Update World Model from Observation
                    self.world_model.update_from_observation(observation)
                    
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

                    # 🧠 AGENT 2.0: HEURISTIC OVERRIDE 🛡️
                    # The Local LLM struggles to use 'launch_app' and prefers 'win' key + typing.
                    # We will intercept 'press_key("win")' and FORCE 'launch_app' if we can infer the intent.
                    
                    if action_name == "press_key" and action_args.get("key") == "win":
                         # Check if the current step mentions "Open" or an App Name
                         step_lower = current_step.lower()
                         if "open" in step_lower or "launch" in step_lower:
                             # Try to extract app name from step text (naive but effective)
                             # e.g. "Open Outlook" -> "Outlook"
                             probable_app = None
                             for word in step_lower.split():
                                 if word not in ["open", "launch", "start", "menu", "app", "application", "the"]:
                                     probable_app = word
                                     break
                             
                             if probable_app:
                                 log.warning(f"🛡️ OVERRIDE: Converting 'press_key(win)' to 'launch_app({probable_app})' for robustness.")
                                 action_name = "launch_app"
                                 action_args = {"name": probable_app}
                                 
                         # If we couldn't guess the app, at least prevent the loop by checking state
                         elif self.world_model.state.is_start_menu_open:
                             log.info(f"Skipping 'win' press, Start Menu is ALREADY open (State-Aware)")
                             # We skip the action but we should probably tell the agent to proceed to typing
                             # For now, let's just continue and hope the next verify cycle catches it
                             continue

                    # Check app spamming (Enhanced with World Model)
                    if action_name == "open_app" and self.world_model.state.active_app == app: # Use WorldModel for context
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
                    # Also update world model after execution!
                    self.world_model.update_from_observation(new_observation)
                    
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
                    # 🎙️ Voice: Failure
                    if self.voice_enabled:
                        self.narrator.say(f"I'm sorry, I failed to complete the task: {current_step}")
                    self.state.complete_task(success=False)
                    return False
            
            log.info("✅ Task completed successfully")
            
            # 🎙️ Voice: Success
            if self.voice_enabled:
                self.narrator.say("I've finished everything! Task is complete.")
            
            self.state.complete_task()
            return True
            
        except Exception as e:
            log.error(f"Task execution failed: {e}")
            # 🎙️ Voice: Failure
            if self.voice_enabled:
                self.voice.speak("Task failed!", rate=180)
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
             
        # 🧠 AGENT 2.0: Ground Truth Active App Detection
        active_window = get_active_window_title()
        if active_window:
            self.world_model.state.active_app = active_window
            obs_text += f"\nACTIVE WINDOW TITLE: {active_window}\n"
            
            # Auto-update heuristics based on title
            if "chrome" in active_window.lower() or "edge" in active_window.lower() or "firefox" in active_window.lower():
                self.world_model.state.is_browser_open = True
             
        return obs_text
            
    def _reason(self, step: str, observation: str, task_context: str) -> Optional[dict]:
        """Reason about a SINGLE step within the plan"""
        # Focus the prompt on the current step
        # 🧠 Inject World State into Prompt
        world_state_str = f"Active App: {self.world_model.state.active_app}\n"
        world_state_str += f"Start Menu Open: {self.world_model.state.is_start_menu_open}\n"
        world_state_str += f"Browser Open: {self.world_model.state.is_browser_open}"
        
        # 🧠 RETRIEVE MEMORY TIPS
        memory_tips = self.memory.get_relevant_feedback(task_context)
        memory_section = ""
        if memory_tips:
            memory_section = f"\n🧠 MEMORY (USER TIPS):\n{memory_tips}\n"
        
        prompt = f"""OVERALL GOAL: {task_context}
CURRENT SUB-TASK: {step}
WORLD STATE:
{world_state_str}
{memory_section}
OBSERVATION:
{observation}

Based on the observation, what is the exact state of the world? 
What might have gone wrong with the previous action?
Determine the next best action.

Thinking Process:
1. Analyse the Active Window: Is it what we expect?
2. Analyse the Visible Text: Do we see the results of previous actions?
3. Decide: Should we retry, proceed, or fix focus?

Output valid JSON action."""
        
        try:
            response = self.llm.generate(prompt, system_prompt=AGENT_SYSTEM_PROMPT_WITH_EXAMPLES)
            return self.parser.parse_llm_output(response)
        except Exception as e:
            log.error(f"Reasoning failed: {e}")
            return None

    async def _execute(self, action: str, args: dict) -> dict:
        """Execute action (Legacy wrapper)"""
        # OS-level actions (MOST POWERFUL)
        if action.startswith("os_"):
            return self.os_executor.execute(action, args)
        
        # Browser actions
        elif action.startswith("browser_"):
            # 🧠 UPDATE: Route open/search to Desktop Executor (Real Chrome)
            if action in ["browser_open", "browser_search"]:
                 return self.desktop_executor.execute(action, args)
            
            # Legacy/Headless actions (extract, specific DOM clicks)
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
