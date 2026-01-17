"""
Action Validator

Validates actions against safety constraints.
"""

from typing import Dict, Any
from core.config import get_config
from utils.logger import log


class ActionValidator:
    """Validates actions before execution"""
    
    def __init__(self):
        config = get_config()
        self.whitelist_enabled = config.safety.enable_whitelist
        self.allowed_apps = [app.lower() for app in config.safety.allowed_apps]
        self.allowed_domains = [domain.lower() for domain in config.safety.allowed_domains]
        self.blocked_actions = config.safety.blocked_actions
        
        log.info("Action validator initialized")
    
    def validate(self, action: str, args: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate an action.
        
        Args:
            action: Action name
            args: Action arguments
            
        Returns:
            (is_valid, error_message)
        """
        # Check blocked actions
        if action in self.blocked_actions:
            msg = f"Action '{action}' is blocked for safety"
            log.warning(msg)
            return False, msg
        
        # Validate specific actions
        if action == "open_app":
            return self._validate_open_app(args)
        
        elif action in ["browser_open", "browser_search"]:
            return self._validate_browser_url(args)
        
        # Default: allow
        return True, ""
    
    def _validate_open_app(self, args: Dict[str, Any]) -> tuple[bool, str]:
        """Validate app opening"""
        if not self.whitelist_enabled:
            return True, ""
        
        app_name = args.get("name", "").lower()
        
        if app_name not in self.allowed_apps:
            msg = f"App '{app_name}' not in whitelist"
            log.warning(msg)
            return False, msg
        
        return True, ""
    
    def _validate_browser_url(self, args: Dict[str, Any]) -> tuple[bool, str]:
        """Validate browser URLs"""
        if not self.whitelist_enabled:
            return True, ""
        
        # Extract domain from URL or query
        url = args.get("url", "")
        query = args.get("query", "")
        
        # For search, allow (Google is default)
        if query and not url:
            return True, ""
        
        # Check domain whitelist
        if url:
            url_lower = url.lower()
            allowed = any(domain in url_lower for domain in self.allowed_domains)
            
            if not allowed:
                msg = f"Domain not in whitelist: {url}"
                log.warning(msg)
                return False, msg
        
        return True, ""
