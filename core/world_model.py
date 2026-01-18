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
    """Snapshot of the world state with symbolic predicates"""
    active_app: str = "unknown"
    focused_element: str = "unknown"
    
    # 🧠 Symbolic Predicates (Agent 2.0)
    is_start_menu_open: bool = False
    is_browser_open: bool = False
    last_action_success: bool = True
    
    # Raw Data
    last_screenshot_path: Optional[str] = None
    browser_url: Optional[str] = None
    visible_text_summary: str = ""

class WorldModel:
    def __init__(self):
        self.state = WorldState()
        self.action_history: List[ActionEntry] = []
        self.context_memory: Dict[str, Any] = {}
        self.task_stack: List[str] = []
        
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
        
        # Update success flag
        self.state.last_action_success = result.get("success", True)
            
    def update_from_observation(self, observation: str):
        """
        🧠 CORE LOGIC: Update symbolic state from raw observation text.
        This parses the "VISIBLE TEXT" section from the observation.
        """
        obs_lower = observation.lower()
        
        # 1. Start Menu Detection
        # Heuristic: Look for common Start Menu text
        start_keywords = [
            "search apps, settings, and documents",
            "pinned",
            "recommended",
            "type here to search",
            "all apps",
            "search", # Lenient
            "user", # Often top right
            "power" # Often bottom right
        ]
        
        # Check if multiple small keywords exist if the big phrase is missing
        start_menu_score = sum(1 for k in start_keywords if k in obs_lower)
        
        # If explicitly seen "pinned" or "recommended" with high confidence
        strong_indicators = ["pinned", "recommended", "all apps", "type here to search"]
        has_strong = any(k in obs_lower for k in strong_indicators)
        
        self.state.is_start_menu_open = has_strong or start_menu_score >= 2
        
        # 2. Browser Detection
        # Heuristic: Look for browser UI elements or specific tag
        self.state.is_browser_open = "browser:" in obs_lower or "addr_bar" in obs_lower
        
        # 3. Update summary
        self.state.visible_text_summary = observation[:500] + "..." if len(observation) > 500 else observation

    def get_recent_history(self, limit: int = 5) -> List[ActionEntry]:
        """Get the last N actions"""
        return self.action_history[-limit:]
        
    def clear_task_state(self):
        """Reset state for a new task"""
        self.task_stack = []
        self.action_history = []
        self.context_memory = {}

