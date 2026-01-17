"""
Task State Management

Tracks the current task state, action history, and observations.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from core.config import get_config
from utils.logger import log


class TaskState:
    """Manages task execution state"""
    
    def __init__(self):
        config = get_config()
        self.state_file = Path(config.memory.state_file)
        self.history_file = Path(config.memory.history_file)
        self.max_history = config.memory.max_history_items
        
        # Create state directory
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Current state
        self.task: Optional[str] = None
        self.status: str = "idle"  # idle, running, completed, failed
        self.step_count: int = 0
        self.action_history: List[Dict[str, Any]] = []
        self.last_observation: str = ""
        self.last_result: Optional[Dict[str, Any]] = None
        
        # 🧠 INTELLIGENCE: State tracking
        self.open_apps: set = set()  # Track which apps are already open
        self.active_app: Optional[str] = None  # Which app is currently focused
        self.last_action: Optional[str] = None  # Last action name
        self.repeat_count: int = 0  # How many times same action repeated
        self.last_screen_hash: Optional[str] = None  # Screen state tracking
        
        log.info("Task state manager initialized")
    
    def start_task(self, task: str):
        """Start a new task"""
        self.task = task
        self.status = "running"
        self.step_count = 0
        self.action_history = []
        self.last_observation = ""
        self.last_result = None
        
        # Reset intelligence state
        self.open_apps = set()
        self.active_app = None
        self.last_action = None
        self.repeat_count = 0
        self.last_screen_hash = None
        
        log.info(f"Task started: {task}")
        self._save_state()
    
    def add_action(self, action: Dict[str, Any], result: Dict[str, Any]):
        """Record an action and its result"""
        self.step_count += 1
        
        entry = {
            "step": self.step_count,
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "result": result
        }
        
        self.action_history.append(entry)
        self.last_result = result
        
        # Trim history if needed
        if len(self.action_history) > self.max_history:
            self.action_history = self.action_history[-self.max_history:]
        
        self._save_state()
        self._save_history()
    
    def update_observation(self, observation: str):
        """Update the last observation"""
        self.last_observation = observation
        self._save_state()
    
    def complete_task(self, success: bool = True):
        """Mark task as completed"""
        self.status = "completed" if success else "failed"
        log.info(f"Task {self.status}: {self.task}")
        self._save_state()
    
    def track_action(self, action_name: str, action_args: Dict[str, Any] = None) -> bool:
        """
        🧠 INTELLIGENCE: Track action and detect repeats
        Returns False if action should be SKIPPED
        """
        # Create a signature for comparison
        current_signature = f"{action_name}:{json.dumps(action_args, sort_keys=True) if action_args else ''}"
        
        # Check if exactly same action repeating
        if current_signature == self.last_action:
            self.repeat_count += 1
        else:
            self.repeat_count = 0
            self.last_action = current_signature
        
        # 🔥 STOP PAGALPAN: Max 3 EXACT SAME actions
        # Some actions like wait/scroll are OK to repeat
        if self.repeat_count >= 3 and action_name not in ["wait", "scroll"]:
            log.warning(f"⚠️ Same action '{action_name}' with same args repeated {self.repeat_count} times - BLOCKING")
            return False
        
        return True
    
    def mark_app_opened(self, app_name: str):
        """Track that an app is now open"""
        self.open_apps.add(app_name)
        self.active_app = app_name
        log.info(f"📱 App tracked as open: {app_name}")
    
    def is_app_open(self, app_name: str) -> bool:
        """Check if app is already open"""
        return app_name in self.open_apps
    
    def set_screen_hash(self, screen_hash: str, skip_check: bool = False) -> bool:
        """
        🧠 INTELLIGENCE: Check if screen changed
        Returns False if screen is SAME (action failed)
        """
        # Skip check for slow actions (apps take time to open)
        if skip_check:
            self.last_screen_hash = screen_hash
            return True
            
        if self.last_screen_hash == screen_hash:
            log.warning("⚠️ Screen unchanged after action - likely FAILED")
            return False
        
        self.last_screen_hash = screen_hash
        return True
    
    def is_running(self) -> bool:
        """Check if task is currently running"""
        return self.status == "running"
    
    def get_summary(self) -> str:
        """Get a human-readable summary"""
        if not self.task:
            return "No active task"
        
        return f"""
Task: {self.task}
Status: {self.status}
Steps: {self.step_count}
Last Action: {self.action_history[-1]['action']['action'] if self.action_history else 'None'}
        """.strip()
    
    def _save_state(self):
        """Save current state to file"""
        state_data = {
            "task": self.task,
            "status": self.status,
            "step_count": self.step_count,
            "last_observation": self.last_observation,
            "last_result": self.last_result,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            with open(self.state_file, "w") as f:
                json.dump(state_data, f, indent=2)
        except Exception as e:
            log.error(f"Failed to save state: {e}")
    
    def _save_history(self):
        """Save action history to file"""
        try:
            with open(self.history_file, "w") as f:
                json.dump(self.action_history, f, indent=2)
        except Exception as e:
            log.error(f"Failed to save history: {e}")
    
    def load_state(self) -> bool:
        """Load state from file"""
        if not self.state_file.exists():
            return False
        
        try:
            with open(self.state_file, "r") as f:
                state_data = json.load(f)
            
            self.task = state_data.get("task")
            self.status = state_data.get("status", "idle")
            self.step_count = state_data.get("step_count", 0)
            self.last_observation = state_data.get("last_observation", "")
            self.last_result = state_data.get("last_result")
            
            log.info("State loaded from file")
            return True
        except Exception as e:
            log.error(f"Failed to load state: {e}")
            return False
