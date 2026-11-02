"""Runtime configuration loaded from agentic.yaml.

Every field has a safe default so the runtime starts with no config file at
all: local Ollama, a sandboxed ./workspace, and approval prompts for anything
that writes, executes, schedules, or drives the desktop.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

CONFIG_FILENAME = "agentic.yaml"
PolicyValue = Literal["auto", "ask", "deny"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProviderConfig(StrictModel):
    type: Literal["ollama", "openai", "anthropic"] = "ollama"
    model: str = "qwen2.5:3b"
    base_url: str | None = None
    api_key_env: str | None = None
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_tokens: int = Field(default=1024, ge=64, le=64_000)
    context_window: int = Field(default=8192, ge=2048, le=1_000_000)
    timeout: int = Field(default=180, ge=5, le=1800)
    # "native" uses the provider's tool-calling API. "prompt" describes tools in
    # the system prompt and parses JSON, which helps small local models.
    tool_mode: Literal["native", "prompt"] = "native"

    def api_key(self) -> str | None:
        return os.getenv(self.api_key_env) if self.api_key_env else None


class PermissionPolicy(StrictModel):
    read: PolicyValue = "auto"
    memory: PolicyValue = "auto"
    network: PolicyValue = "auto"
    write: PolicyValue = "ask"
    execute: PolicyValue = "ask"
    schedule: PolicyValue = "ask"
    desktop: PolicyValue = "ask"


class LimitsConfig(StrictModel):
    max_steps: int = Field(default=12, ge=1, le=100)
    max_parallel: int = Field(default=3, ge=1, le=16)
    max_tasks: int = Field(default=8, ge=1, le=32)
    max_revisions: int = Field(default=1, ge=0, le=5)
    max_delegation_depth: int = Field(default=2, ge=0, le=5)
    tool_timeout: int = Field(default=60, ge=1, le=3600)
    tool_output_chars: int = Field(default=12_000, ge=500, le=200_000)
    approval_timeout: int = Field(default=300, ge=5, le=86_400)


class NetworkConfig(StrictModel):
    # Empty means any public host. Private and loopback addresses are always
    # refused unless allow_private_hosts is true.
    allowed_domains: list[str] = Field(default_factory=list)
    allow_private_hosts: bool = False


class MCPServerConfig(StrictModel):
    command: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    permission: Literal["read", "memory", "network", "write", "execute", "desktop"] = "execute"
    enabled: bool = True


class GatewayConfig(StrictModel):
    host: str = "127.0.0.1"
    port: int = Field(default=8765, ge=1, le=65_535)
    token_env: str = "AGENTIC_TOKEN"


class TelegramConfig(StrictModel):
    enabled: bool = False
    token_env: str = "TELEGRAM_BOT_TOKEN"
    allowed_chat_ids: list[int] = Field(default_factory=list)


class ChannelsConfig(StrictModel):
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)


class SchedulerConfig(StrictModel):
    enabled: bool = True
    poll_seconds: int = Field(default=15, ge=1, le=3600)
    # Nobody is watching a scheduled run, so "ask" becomes "deny" unless the
    # permission is listed here.
    unattended_permissions: list[str] = Field(default_factory=lambda: ["read", "memory", "network"])


class Settings(StrictModel):
    default_provider: str = "local"
    providers: dict[str, ProviderConfig] = Field(
        default_factory=lambda: {"local": ProviderConfig()}
    )
    workspace: str = "workspace"
    data_dir: str = ".agentic"
    heads_dir: str = "heads"
    skills_dir: str = "skills"
    permissions: PermissionPolicy = Field(default_factory=PermissionPolicy)
    limits: LimitsConfig = Field(default_factory=LimitsConfig)
    network: NetworkConfig = Field(default_factory=NetworkConfig)
    mcp_servers: dict[str, MCPServerConfig] = Field(default_factory=dict)
    gateway: GatewayConfig = Field(default_factory=GatewayConfig)
    channels: ChannelsConfig = Field(default_factory=ChannelsConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)

    # Not part of the file: the directory relative paths resolve against.
    root: Path = Field(default_factory=Path.cwd, exclude=True)

    def resolve(self, value: str) -> Path:
        path = Path(value).expanduser()
        return path if path.is_absolute() else (self.root / path)

    @property
    def workspace_path(self) -> Path:
        return self.resolve(self.workspace).resolve()

    @property
    def data_path(self) -> Path:
        return self.resolve(self.data_dir).resolve()

    def provider(self, name: str | None = None) -> ProviderConfig:
        key = name or self.default_provider
        if key not in self.providers:
            raise KeyError(
                f"Unknown provider {key!r}. Configured: {', '.join(sorted(self.providers))}"
            )
        return self.providers[key]


def load_settings(path: str | Path | None = None) -> Settings:
    """Load settings from a file, or from ./agentic.yaml when present."""
    config_path = Path(path) if path else Path.cwd() / CONFIG_FILENAME
    if not config_path.exists():
        if path:
            raise FileNotFoundError(f"Config file not found: {config_path}")
        return Settings(root=Path.cwd())

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"{config_path} must contain a YAML mapping")
    raw.pop("root", None)
    return Settings(**raw, root=config_path.resolve().parent)
