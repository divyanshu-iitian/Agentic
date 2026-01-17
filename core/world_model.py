"""
World Model - The Agent's Contextual Memory 🧠

This module maintains the state of the world as perceived by the agent.
It tracks:
1. Active Application (where are we?)
2. Interaction History (what did we just do?)
3. Observed State (what do we see?)
4. Task Context (what are we trying to achieve?)
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import time

@dataclass
class ActionEntry:
    """Record of an action taken"""
    name: str
    args: Dict[str, Any]
    timestamp: float
    result: Dict[str, Any]
    thought: str = ""

@dataclass
class WorldState:
    """Snapshot of the world state"""
    active_app: str = "unknown"
    focused_element: str = "unknown"
    last_screenshot_path: Optional[str] = None
    browser_url: Optional[str] = None
    
class WorldModel:
    def __init__(self):
        self.state = WorldState()
        self.action_history: List[ActionEntry] = []
        self.context_memory: Dict[str, Any] = {} # For "remembering" things like "found_email"
        self.task_stack: List[str] = [] # Stack of active sub-tasks
        
    def update_context(self, key: str, value: Any):
        """Update a specific context variable"""
        self.context_memory[key] = value
        
    def get_context(self, key: str) -> Optional[Any]:
        """Retrieve context value"""
        return self.context_memory.get(key)
        
    def record_action(self, action: str, args: dict, result: dict, thought: str = ""):
        """Log an action into short-term memory"""
        entry = ActionEntry(
            name=action,
            args=args,
            timestamp=time.time(),
            result=result,
            thought=thought
        )
        self.action_history.append(entry)
        
        # Heuristics to update state based on action
        if action == "open_app":
            self.state.active_app = args.get("name", "unknown")
        elif action == "browser_open":
            self.state.active_app = "browser"
            self.state.browser_url = args.get("url")
            
    def get_recent_history(self, limit: int = 5) -> List[ActionEntry]:
        """Get the last N actions"""
        return self.action_history[-limit:]
        
    def clear_task_state(self):
        """Reset state for a new task"""
        self.task_stack = []
        self.action_history = []
        # We keep context_memory? Maybe clear it too depending on user intent.
        # For now, clear it to ensure "fresh start" as requested by user.
        self.context_memory = {}
