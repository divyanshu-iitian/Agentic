"""
OS-Level Action Schemas

Pydantic models for OS-level actions.
"""

from typing import Dict, Any, Literal
from pydantic import BaseModel, Field


class OSOpenAppAction(BaseModel):
    """Open app using OS commands"""
    action: Literal["os_open_app"] = "os_open_app"
    args: Dict[str, str] = Field(...)
    
    def validate_args(self):
        assert "name" in self.args, "Missing 'name' in args"


class OSRunCommandAction(BaseModel):
    """Run OS command (PowerShell/CMD)"""
    action: Literal["os_run_command"] = "os_run_command"
    args: Dict[str, Any] = Field(...)
    
    def validate_args(self):
        assert "command" in self.args, "Missing 'command' in args"


class OSOpenURLAction(BaseModel):
    """Open URL using OS default browser"""
    action: Literal["os_open_url"] = "os_open_url"
    args: Dict[str, str] = Field(...)
    
    def validate_args(self):
        assert "url" in self.args, "Missing 'url' in args"


class OSFileOperationAction(BaseModel):
    """File operations using OS"""
    action: Literal["os_file_operation"] = "os_file_operation"
    args: Dict[str, Any] = Field(...)
    
    def validate_args(self):
        assert "operation" in self.args, "Missing 'operation' in args"
        assert "path" in self.args, "Missing 'path' in args"


class OSWindowControlAction(BaseModel):
    """Window management using OS"""
    action: Literal["os_window_control"] = "os_window_control"
    args: Dict[str, Any] = Field(...)
    
    def validate_args(self):
        assert "operation" in self.args, "Missing 'operation' in args"


class OSClipboardAction(BaseModel):
    """Clipboard operations"""
    action: Literal["os_clipboard"] = "os_clipboard"
    args: Dict[str, Any] = Field(...)
    
    def validate_args(self):
        assert "operation" in self.args, "Missing 'operation' in args"


class OSSystemControlAction(BaseModel):
    """System-level controls"""
    action: Literal["os_system_control"] = "os_system_control"
    args: Dict[str, Any] = Field(...)
    
    def validate_args(self):
        assert "operation" in self.args, "Missing 'operation' in args"
