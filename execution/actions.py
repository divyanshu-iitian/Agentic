"""
Action Schemas

Pydantic models for all agent actions.
Ensures type safety and validation.
"""

from typing import Dict, Any, Literal
from pydantic import BaseModel, Field


# ============= Desktop Actions =============

class OpenAppAction(BaseModel):
    """Open an application"""
    action: Literal["open_app"] = "open_app"
    args: Dict[str, str] = Field(...)
    
    def validate_args(self):
        assert "name" in self.args, "Missing 'name' in args"


class ClickAction(BaseModel):
    """Click at coordinates"""
    action: Literal["click"] = "click"
    args: Dict[str, int] = Field(...)
    
    def validate_args(self):
        assert "x" in self.args, "Missing 'x' in args"
        assert "y" in self.args, "Missing 'y' in args"


class TypeAction(BaseModel):
    """Type text"""
    action: Literal["type"] = "type"
    args: Dict[str, str] = Field(...)
    
    def validate_args(self):
        assert "text" in self.args, "Missing 'text' in args"


class ScrollAction(BaseModel):
    """Scroll by amount"""
    action: Literal["scroll"] = "scroll"
    args: Dict[str, int] = Field(...)
    
    def validate_args(self):
        assert "amount" in self.args, "Missing 'amount' in args"


class WaitAction(BaseModel):
    """Wait for seconds"""
    action: Literal["wait"] = "wait"
    args: Dict[str, float] = Field(...)
    
    def validate_args(self):
        assert "seconds" in self.args, "Missing 'seconds' in args"


# ============= 🧠 SEMANTIC VS CODE ACTIONS =============

class VSCodeOpenAction(BaseModel):
    """Open VS Code (semantic action)"""
    action: Literal["vscode_open"] = "vscode_open"
    args: Dict = Field(default_factory=dict)


class VSCodeNewFileAction(BaseModel):
    """Create new file in VS Code (semantic action)"""
    action: Literal["vscode_new_file"] = "vscode_new_file"
    args: Dict = Field(default_factory=dict)


class VSCodeSaveFileAction(BaseModel):
    """Save current file in VS Code (semantic action)"""
    action: Literal["vscode_save_file"] = "vscode_save_file"
    args: Dict[str, str] = Field(default_factory=dict)
    
    def validate_args(self):
        # filename is optional
        pass


# ============= 🐙 GITHUB ACTIONS =============

class GitHubContributeAction(BaseModel):
    """Make an open source contribution"""
    action: Literal["github_contribute"] = "github_contribute"
    args: Dict[str, Any] = Field(default_factory=dict)
    
    def validate_args(self):
        pass  # All parameters are optional


class GitHubSearchProjectsAction(BaseModel):
    """Search for GitHub projects"""
    action: Literal["github_search_projects"] = "github_search_projects"
    args: Dict[str, Any] = Field(default_factory=dict)
    
    def validate_args(self):
        pass  # All parameters are optional


class GitHubCreatePRAction(BaseModel):
    """Create a pull request"""
    action: Literal["github_create_pr"] = "github_create_pr"
    args: Dict[str, Any] = Field(...)
    
    def validate_args(self):
        assert "repo" in self.args, "Missing 'repo' in args"
        assert "title" in self.args, "Missing 'title' in args"


# ============= 👁️ VISION ACTIONS =============

class VisionAnalyzeAction(BaseModel):
    """Analyze what's visible in camera"""
    action: Literal["vision_analyze"] = "vision_analyze"
    args: Dict[str, str] = Field(default_factory=dict)
    
    def validate_args(self):
        pass  # Query is optional


class VisionAnswerAction(BaseModel):
    """Answer a visual question about camera feed"""
    action: Literal["vision_answer"] = "vision_answer"
    args: Dict[str, str] = Field(...)
    
    def validate_args(self):
        assert "question" in self.args, "Missing 'question' in args"


class VisionDetectPersonAction(BaseModel):
    """Detect if person is present in camera"""
    action: Literal["vision_detect_person"] = "vision_detect_person"
    args: Dict = Field(default_factory=dict)
    
    def validate_args(self):
        pass  # No required args


# ============= Browser Actions =============

class BrowserOpenAction(BaseModel):
    """Open URL in browser"""
    action: Literal["browser_open"] = "browser_open"
    args: Dict[str, str] = Field(...)
    
    def validate_args(self):
        assert "url" in self.args, "Missing 'url' in args"


class BrowserSearchAction(BaseModel):
    """Search in browser"""
    action: Literal["browser_search"] = "browser_search"
    args: Dict[str, str] = Field(...)
    
    def validate_args(self):
        assert "query" in self.args, "Missing 'query' in args"


class BrowserClickAction(BaseModel):
    """Click element in browser"""
    action: Literal["browser_click"] = "browser_click"
    args: Dict[str, str] = Field(...)
    
    def validate_args(self):
        assert "selector" in self.args, "Missing 'selector' in args"


class BrowserScrollAction(BaseModel):
    """Scroll in browser"""
    action: Literal["browser_scroll"] = "browser_scroll"
    args: Dict[str, int] = Field(...)
    
    def validate_args(self):
        assert "amount" in self.args, "Missing 'amount' in args"


class BrowserExtractAction(BaseModel):
    """Extract information from browser"""
    action: Literal["browser_extract"] = "browser_extract"
    args: Dict[str, str] = Field(...)
    
    def validate_args(self):
        assert "goal" in self.args, "Missing 'goal' in args"


# ============= Control Actions =============

class StopAction(BaseModel):
    """Stop execution"""
    action: Literal["stop"] = "stop"
    args: Dict = Field(default_factory=dict)


# ============= Union Type =============

AgentAction = (
    OpenAppAction | ClickAction | TypeAction | ScrollAction | WaitAction |
    VSCodeOpenAction | VSCodeNewFileAction | VSCodeSaveFileAction |
    GitHubContributeAction | GitHubSearchProjectsAction | GitHubCreatePRAction |
    VisionAnalyzeAction | VisionAnswerAction | VisionDetectPersonAction |
    BrowserOpenAction | BrowserSearchAction | BrowserClickAction | 
    BrowserScrollAction | BrowserExtractAction | StopAction
)


# ============= Action Registry =============

ACTION_TYPES = {
    "open_app": OpenAppAction,
    "click": ClickAction,
    "type": TypeAction,
    "scroll": ScrollAction,
    "wait": WaitAction,
    "vscode_open": VSCodeOpenAction,
    "vscode_new_file": VSCodeNewFileAction,
    "vscode_save_file": VSCodeSaveFileAction,
    "github_contribute": GitHubContributeAction,
    "github_search_projects": GitHubSearchProjectsAction,
    "github_create_pr": GitHubCreatePRAction,
    "vision_analyze": VisionAnalyzeAction,
    "vision_answer": VisionAnswerAction,
    "vision_detect_person": VisionDetectPersonAction,
    "browser_open": BrowserOpenAction,
    "browser_search": BrowserSearchAction,
    "browser_click": BrowserClickAction,
    "browser_scroll": BrowserScrollAction,
    "browser_extract": BrowserExtractAction,
    "stop": StopAction,
}


def parse_action(action_dict: Dict[str, Any]) -> AgentAction:
    """
    Parse and validate action dictionary.
    
    Args:
        action_dict: Raw action from LLM
        
    Returns:
        Validated action object
        
    Raises:
        ValueError: If action is invalid
    """
    action_name = action_dict.get("action")
    
    if action_name not in ACTION_TYPES:
        raise ValueError(f"Unknown action: {action_name}")
    
    action_class = ACTION_TYPES[action_name]
    action_obj = action_class(**action_dict)
    action_obj.validate_args()
    
    return action_obj
