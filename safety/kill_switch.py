"""
Emergency Kill Switch

Provides emergency stop functionality.
"""

import sys
import keyboard as kb
from typing import Callable, Optional
from core.config import get_config
from utils.logger import log


class KillSwitch:
    """Emergency stop mechanism"""
    
    def __init__(self, callback: Optional[Callable] = None):
        config = get_config()
        self.hotkey = config.safety.emergency_kill_hotkey
        self.callback = callback or self._default_callback
        self.active = False
        
        log.info(f"Kill switch initialized: {self.hotkey}")
    
    def activate(self):
        """Activate the kill switch listener"""
        if self.active:
            return
        
        try:
            kb.add_hotkey(self.hotkey, self._trigger)
            self.active = True
            log.info("Kill switch ACTIVE")
        except Exception as e:
            log.error(f"Failed to activate kill switch: {e}")
    
    def deactivate(self):
        """Deactivate the kill switch"""
        if not self.active:
            return
        
        try:
            kb.remove_hotkey(self.hotkey)
            self.active = False
            log.info("Kill switch deactivated")
        except Exception as e:
            log.error(f"Failed to deactivate kill switch: {e}")
    
    def _trigger(self):
        """Called when kill switch is triggered"""
        log.critical("🚨 KILL SWITCH TRIGGERED 🚨")
        self.callback()
    
    def _default_callback(self):
        """Default emergency stop action"""
        log.critical("Emergency stop: Exiting program")
        sys.exit(0)


class ActionLimiter:
    """Limits number of actions per task"""
    
    def __init__(self):
        config = get_config()
        self.max_actions = config.safety.max_actions_per_task
        self.action_count = 0
        
        log.info(f"Action limiter: max {self.max_actions} actions")
    
    def reset(self):
        """Reset action counter"""
        self.action_count = 0
    
    def increment(self) -> bool:
        """
        Increment action counter.
        
        Returns:
            True if within limit, False if exceeded
        """
        self.action_count += 1
        
        if self.action_count > self.max_actions:
            log.error(f"Action limit exceeded: {self.action_count}/{self.max_actions}")
            return False
        
        if self.action_count == self.max_actions:
            log.warning("Action limit reached")
        
        return True
    
    def get_remaining(self) -> int:
        """Get remaining actions"""
        return max(0, self.max_actions - self.action_count)
