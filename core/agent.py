"""
Main Agent Orchestration

Core agent loop: Observe → Reason → Plan → Execute → Feedback

NOW WITH PRODUCTION-GRADE PERCEPTION & INTERACTION!
"""

from core.config import get_config
from core.memory import LongTermMemory
from core.skills import SkillRegistry
from core.state import TaskState
from execution.browser_executor import BrowserExecutor
from execution.desktop_executor import DesktopExecutor
from interaction.icon_fallback import IconFallback
from interaction.keyboard_policy import KeyboardPolicy
from interaction.text_anchor_clicker import TextAnchorClicker
from llm.ollama_client import OllamaClient
from llm.parser import JSONParser
from llm.prompt import AGENT_SYSTEM_PROMPT_WITH_EXAMPLES, build_user_prompt
from observation.screen_capture import ScreenCapture
from perception.change_detector import ChangeDetector
from perception.ocr_extractor import OCRExtractor

# 🧠 NEW: Perception & Interaction layers
from perception.screen_observer import ScreenObserver
from perception.ui_state_builder import UIStateBuilder
from planning.action_validator import ActionValidator
from safety.kill_switch import ActionLimiter, KillSwitch
from utils.logger import log


class Agent:
    """Main autonomous agent with intelligent perception"""

    def __init__(self):
        self.config = get_config()

        # Initialize components
        self.state = TaskState()
        self.llm = OllamaClient()
        self.parser = JSONParser()
        self.validator = ActionValidator()
        self.limiter = ActionLimiter()
        self.skills = SkillRegistry()
        self.memory = LongTermMemory()

        # Executors
        self.desktop_executor = DesktopExecutor()
        self.browser_executor = BrowserExecutor()

        # Legacy observation (keeping for compatibility)
        self.screen_capture = ScreenCapture()

        # 🧠 NEW: Perception layer
        self.screen_observer = ScreenObserver(
            save_observations=self.config.observation.screenshot_on_action
        )
        self.ocr_extractor = OCRExtractor(min_confidence=30.0)
        self.ui_state_builder = UIStateBuilder()
        self.change_detector = ChangeDetector()

        # 🧠 NEW: Interaction layer
        self.keyboard_policy = KeyboardPolicy()
        self.text_clicker = TextAnchorClicker()
        self.icon_fallback = IconFallback()

        # Perception state
        self.current_ui_state = None
        self.last_ui_state = None
        self.last_observation = None

        # Safety
        self.kill_switch = KillSwitch(callback=self.emergency_stop)

        self.running = False

        log.info("🤖 Agent initialized with INTELLIGENT PERCEPTION")

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

    def learn_from_feedback(self, feedback: str) -> None:
        """Persist user feedback for future tasks with similar keywords."""
        task = self.state.task or "general"
        steps = [
            entry.get("action", {}).get("action", "unknown") for entry in self.state.action_history
        ]
        self.memory.save_feedback(task, feedback, steps)

    async def execute_task(self, task: str) -> bool:
        """
        Execute a task autonomously.

        Args:
            task: Natural language task description

        Returns:
            True if successful
        """
        log.info(f"📋 New task: {task}")

        # Initialize task state
        self.state.start_task(task)
        self.limiter.reset()

        try:
            while self.running and self.state.is_running():
                # Check action limit
                if not self.limiter.increment():
                    log.error("Action limit exceeded, stopping")
                    self.state.complete_task(success=False)
                    break

                # STEP 1: OBSERVE
                observation = await self._observe()
                self.state.update_observation(observation)

                # STEP 2: REASON (LLM decides next action)
                action_json = self._reason(task, observation)

                if action_json is None:
                    log.error("Failed to get valid action from LLM")
                    self.state.complete_task(success=False)
                    break

                # STEP 3: VALIDATE
                action_name = action_json["action"]
                action_args = action_json.get("args", {})

                # 🧠 INTELLIGENCE: Check repeat action
                if not self.state.track_action(action_name, action_args):
                    log.error(f"🛑 Repeated action blocked: {action_name}")
                    self.state.complete_task(success=False)
                    break

                # 🧠 INTELLIGENCE: Skip if app already open
                if action_name == "open_app" or action_name == "vscode_open":
                    app_name = action_args.get(
                        "name", "vscode" if action_name == "vscode_open" else ""
                    )
                    if self.state.is_app_open(app_name):
                        log.info(f"⏭️ Skipping - {app_name} already open")
                        # Don't count this as a real action
                        self.state.last_action = None  # Reset to prevent false repeat detection
                        continue

                is_valid, error_msg = self.validator.validate(action_name, action_args)
                if not is_valid:
                    log.error(f"Action validation failed: {error_msg}")
                    self.state.complete_task(success=False)
                    break

                # Check for stop action
                if action_name == "stop":
                    log.info("✅ Task completed (stop action)")
                    self.state.complete_task(success=True)
                    break

                # STEP 4: EXECUTE
                result = await self._execute(action_name, action_args)

                # 🧠 INTELLIGENCE: Track opened apps
                if result.get("success") and (
                    action_name == "open_app" or action_name == "vscode_open"
                ):
                    app_name = action_args.get(
                        "name", "vscode" if action_name == "vscode_open" else ""
                    )
                    self.state.mark_app_opened(app_name)

                # STEP 5: FEEDBACK
                self.state.add_action(action_json, result)

                if not result.get("success", False):
                    log.warning(f"Action failed: {result.get('error')}")
                    # Continue anyway (agent should adapt)

                log.info(f"Step {self.state.step_count}: {action_name} → {result.get('success')}")

            return self.state.status == "completed"

        except Exception as e:
            log.error(f"Task execution failed: {e}")
            self.state.complete_task(success=False)
            return False

    async def _observe(self) -> str:
        """
        Gather current state observation using INTELLIGENT PERCEPTION.

        NEW PERCEPTION PIPELINE:
        1. Capture screen
        2. Extract text with OCR
        3. Build symbolic UI state
        4. Detect changes from last observation
        5. Provide rich, semantic observation

        Returns:
            Symbolic observation string (not raw pixels!)
        """
        observation_parts = []

        # STEP 1: Capture screen
        screen_obs = self.screen_observer.observe()

        # STEP 2: Extract text
        text_elements = self.ocr_extractor.extract(screen_obs.image)

        # STEP 3: Build symbolic UI state
        self.current_ui_state = self.ui_state_builder.build_state(text_elements)

        # STEP 4: Detect changes
        if self.last_ui_state:
            change = self.change_detector.detect_change(
                self.last_ui_state, self.current_ui_state, self.last_observation, screen_obs
            )

            if not change.changed:
                observation_parts.append(
                    "⚠️ WARNING: No UI change detected - last action may have failed"
                )
            else:
                observation_parts.append(f"✓ Change detected: {change.details}")

        # STEP 5: Build symbolic observation
        observation_parts.append(f"\\n🔍 UI STATE:\\n{self.current_ui_state}")

        # Add OCR text summary
        if text_elements:
            text_summary = self.ocr_extractor.get_text_summary(text_elements, max_length=300)
            observation_parts.append(f"\\n📝 Visible Text: {text_summary}")

        # Browser state (if active)
        if self.browser_executor.page is not None:
            dom_summary = await self.browser_executor.get_dom_summary()
            observation_parts.append(f"\\n🌐 Browser: {dom_summary}")

        # Previous action result
        if self.state.last_result:
            observation_parts.append(f"\\n📊 Last result: {self.state.last_result}")

        # Update state for next comparison
        self.last_ui_state = self.current_ui_state
        self.last_observation = screen_obs

        return "\\n".join(observation_parts)

    def _reason(self, task: str, observation: str) -> dict | None:
        """
        Use LLM to decide next action.

        Args:
            task: Original task
            observation: Current observation

        Returns:
            Parsed action JSON or None
        """
        # Build prompt
        user_prompt = build_user_prompt(task, observation, self.state.step_count)

        # Get LLM response
        try:
            skill_prompt = self.skills.prompt_for(task)
            memory_prompt = self.memory.get_relevant_feedback(task)
            if memory_prompt:
                memory_prompt = f"\n\nRELEVANT USER FEEDBACK:\n{memory_prompt}"
            response = self.llm.generate(
                prompt=user_prompt,
                system_prompt=(AGENT_SYSTEM_PROMPT_WITH_EXAMPLES + skill_prompt + memory_prompt),
            )
        except Exception as e:
            log.error(f"LLM generation failed: {e}")
            return None

        # Parse JSON
        action_json = self.parser.parse_llm_output(response)

        if action_json is None:
            log.warning(f"Failed to parse LLM output: {response[:100]}")

        return action_json

    async def _execute(self, action: str, args: dict) -> dict:
        """
        Execute an action.

        Args:
            action: Action name
            args: Action arguments

        Returns:
            Execution result
        """
        if action.startswith("browser_"):
            return await self.browser_executor.execute(action, args)

        # Desktop actions
        else:
            return self.desktop_executor.execute(action, args)
