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
        
        # 0. Filter out agent's own UI elements (CRITICAL!)
        # Remove agent's own UI text to avoid confusion
        agent_ui_keywords = [
            "agentic ai",
            "agentic —",
            "press ctrl+space",
            "enter command",
            "type your command"
        ]
        
        # Create filtered observation for analysis
        filtered_obs = obs_lower
        for keyword in agent_ui_keywords:
            filtered_obs = filtered_obs.replace(keyword, "")
        
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
        start_menu_score = sum(1 for k in start_keywords if k in filtered_obs)
        
        # If explicitly seen "pinned" or "recommended" with high confidence
        strong_indicators = ["pinned", "recommended", "all apps", "type here to search"]
        has_strong = any(k in filtered_obs for k in strong_indicators)
        
        self.state.is_start_menu_open = has_strong or start_menu_score >= 2
        
        # 2. Browser Detection (ENHANCED!)
        # Multiple signals for browser detection
        browser_signals = {
            # Chrome-specific
            "chrome": 2,
            "google chrome": 3,
            "new tab": 2,
            "google search": 2,
            
            # Generic browser
            "browser:": 3,
            "addr_bar": 3,
            "address bar": 2,
            
            # URL patterns
            "http": 1,
            "https": 1,
            "www.": 1,
            ".com": 1,
            
            # Browser UI
            "bookmarks": 1,
            "extensions": 1,
            "settings": 1,  # Can be ambiguous
            "history": 1,
            
            # Search engines
            "google": 1,
            "youtube": 2,
            "github": 2
        }
        
        browser_score = 0
        for signal, weight in browser_signals.items():
            if signal in filtered_obs:
                browser_score += weight
        
        # Browser is open if score >= 3 OR explicit browser tag
        self.state.is_browser_open = browser_score >= 3 or "browser:" in obs_lower
        
        # 3. Active App Detection (NEW!)
        # Try to determine what app is actually active
        if "chrome" in filtered_obs or "google" in filtered_obs:
            self.state.active_app = "Chrome"
        elif "edge" in filtered_obs or "microsoft edge" in filtered_obs:
            self.state.active_app = "Edge"
        elif "firefox" in filtered_obs:
            self.state.active_app = "Firefox"
        elif "vs code" in filtered_obs or "visual studio code" in filtered_obs:
            self.state.active_app = "VS Code"
        elif "notepad" in filtered_obs:
            self.state.active_app = "Notepad"
        elif self.state.is_start_menu_open:
            self.state.active_app = "Start Menu"
        else:
            # Keep previous or set to unknown
            if not self.state.active_app or self.state.active_app == "unknown":
                self.state.active_app = "Desktop"
        
        # 4. Update summary (filtered version)
        self.state.visible_text_summary = observation[:500] + "..." if len(observation) > 500 else observation

    def get_recent_history(self, limit: int = 5) -> List[ActionEntry]:
        """Get the last N actions"""
        return self.action_history[-limit:]
        
    def clear_task_state(self):
        """Reset state for a new task"""
        self.task_stack = []
        self.action_history = []
        self.context_memory = {}

