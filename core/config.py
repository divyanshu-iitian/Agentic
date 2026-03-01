"""
Configuration Management

Loads and validates agent configuration from config.yaml
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List
from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """LLM configuration"""
    provider: str = "ollama"
    model: str = "qwen2.5:7b"
    base_url: str = "http://localhost:11434"
    temperature: float = 0.1
    max_tokens: int = 512
    timeout: int = 30


class SafetyConfig(BaseModel):
    """Safety constraints"""
    max_actions_per_task: int = 50
    emergency_kill_hotkey: str = "ctrl+alt+q"
    enable_whitelist: bool = True
    allowed_apps: List[str] = Field(default_factory=list)
    allowed_domains: List[str] = Field(default_factory=list)
    blocked_actions: List[str] = Field(default_factory=list)


class UIConfig(BaseModel):
    """UI settings"""
    activation_hotkey: str = "ctrl+space"
    always_on_top: bool = True
    window_width: int = 600
    window_height: int = 100
    transparency: float = 0.95
    font_size: int = 12


class ObservationConfig(BaseModel):
    """Observation settings"""
    screenshot_on_action: bool = True
    ocr_enabled: bool = True
    ocr_languages: List[str] = Field(default_factory=lambda: ["en"])
    dom_summarization: bool = True
    max_dom_elements: int = 100


class DesktopExecutionConfig(BaseModel):
    """Desktop execution settings"""
    click_delay: float = 0.5
    type_delay: float = 0.1
    screenshot_before_click: bool = True


class BrowserExecutionConfig(BaseModel):
    """Browser execution settings"""
    headless: bool = False
    viewport_width: int = 1920
    viewport_height: int = 1080
    default_timeout: int = 10000
    wait_after_navigation: int = 2


class ExecutionConfig(BaseModel):
    """Execution settings"""
    desktop: DesktopExecutionConfig = Field(default_factory=DesktopExecutionConfig)
    browser: BrowserExecutionConfig = Field(default_factory=BrowserExecutionConfig)


class LoggingConfig(BaseModel):
    """Logging settings"""
    level: str = "INFO"
    file: str = "logs/agent.log"
    max_size_mb: int = 50
    backup_count: int = 5
    console_output: bool = True


class MemoryConfig(BaseModel):
    """Memory settings"""
    state_file: str = "state/current_task.json"
    history_file: str = "state/action_history.json"
    max_history_items: int = 100


class Config(BaseModel):
    """Main configuration"""
    llm: LLMConfig = Field(default_factory=LLMConfig)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    observation: ObservationConfig = Field(default_factory=ObservationConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)


def load_config(config_path: str = "config.yaml") -> Config:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to config.yaml
        
    Returns:
        Validated Config object
    """
    config_file = Path(config_path)
    
    if not config_file.exists():
        print(f"⚠️ Config file not found at {config_path}, using defaults")
        return Config()
    
    with open(config_file, "r") as f:
        config_dict = yaml.safe_load(f)
    
    return Config(**config_dict)


# Global config instance
_config: Config | None = None


def get_config() -> Config:
    """Get the global configuration instance"""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config() -> Config:
    """Reload configuration from file"""
    global _config
    _config = load_config()
    return _config
