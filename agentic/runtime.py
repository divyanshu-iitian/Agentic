"""The runtime wires settings, providers, tools, heads, memory, and events together.

Every surface (CLI, gateway, chat channels, scheduler) drives the same
Runtime, so a run looks identical in the event log wherever it started.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass

from agentic.agent import Head, HeadResult
from agentic.approvals import ApprovalGate, Approver
from agentic.config import ProviderConfig, Settings
from agentic.events import EventBus
from agentic.heads import HeadProfile, load_heads
from agentic.llm.base import Message, Provider
from agentic.llm.providers import build_provider
from agentic.skills import SkillRegistry
from agentic.store import Store
from agentic.swarm import Swarm
from agentic.tools import ToolRegistry, builtin_tools
from agentic.tools.mcp import MCPClient, mcp_tools

ProviderFactory = Callable[[str, ProviderConfig], Provider]
log = logging.getLogger("agentic.runtime")

CHAT_HELP = """Commands:
/swarm <goal>   run the full multi-head team on a goal
/run <goal>     run the assistant head as a one-off task
/remember <x>   save a long-term memory
/memories       list recent memories
/schedules      list scheduled automations
/reset          clear this conversation
/help           show this help"""


@dataclass
class RunOutcome:
    run_id: str
    output: str
    ok: bool


class Runtime:
    def __init__(
        self,
        settings: Settings,
        *,
        approver: Approver | None = None,
        provider_factory: ProviderFactory | None = None,
        store: Store | None = None,
        permission_overrides: dict[str, str] | None = None,
    ):
        self.settings = settings
        settings.workspace_path.mkdir(parents=True, exist_ok=True)
        self.store = store or Store(settings.data_path / "agentic.db")
        self.bus = EventBus(self.store)
        self.tools = ToolRegistry()
        for tool in builtin_tools():
            self.tools.register(tool)
        self.heads: dict[str, HeadProfile] = load_heads(settings.resolve(settings.heads_dir))
        if "assistant" not in self.heads:
            raise RuntimeError("The built-in 'assistant' head is missing")
        self.skills = SkillRegistry(settings.resolve(settings.skills_dir))
        self.gate = ApprovalGate(
            settings.permissions,
            approver,
            timeout=settings.limits.approval_timeout,
            overrides=permission_overrides,
            unattended=set(settings.scheduler.unattended_permissions),
        )
        self.provider_factory = provider_factory or build_provider
        self._providers: dict[str, Provider] = {}
        self.mcp_clients: list[MCPClient] = []
        self.mcp_errors: dict[str, str] = {}

    # Providers ------------------------------------------------------------

    def provider_for(self, profile: HeadProfile) -> Provider:
        name = profile.provider or self.settings.default_provider
        if name not in self._providers:
            self._providers[name] = self.provider_factory(name, self.settings.provider(name))
        return self._providers[name]

    # MCP ------------------------------------------------------------------

    async def start_mcp(self) -> None:
        for name, config in self.settings.mcp_servers.items():
            if not config.enabled:
                continue
            client = MCPClient(name, config, timeout=self.settings.limits.tool_timeout)
            try:
                await asyncio.to_thread(client.start)
                tools = await asyncio.to_thread(mcp_tools, client)
            except Exception as exc:
                client.close()
                self.mcp_errors[name] = str(exc)
                log.warning("MCP server %s failed to start: %s", name, exc)
                continue
            for tool in tools:
                self.tools.register(tool)
            self.mcp_clients.append(client)
            log.info("MCP server %s: %d tools", name, len(tools))

    def close(self) -> None:
        for client in self.mcp_clients:
            client.close()
        self.mcp_clients.clear()

    # Runs -----------------------------------------------------------------

    async def run_head(
        self,
        name: str,
        task: str,
        *,
        run_id: str,
        origin: str = "cli",
        depth: int = 0,
        context: str = "",
        history: list[Message] | None = None,
    ) -> HeadResult:
        profile = self.heads.get(name)
        if profile is None:
            raise KeyError(f"Unknown head {name!r}")
        return await Head(self, profile).run(
            task, run_id=run_id, origin=origin, depth=depth, context=context, history=history
        )

    async def run(
        self,
        goal: str,
        *,
        mode: str = "agent",
        head: str = "assistant",
        origin: str = "cli",
        history: list[Message] | None = None,
        critic: bool = True,
        run_id: str | None = None,
    ) -> RunOutcome:
        if mode not in {"agent", "swarm"}:
            raise ValueError("mode must be 'agent' or 'swarm'")
        if head not in self.heads:
            raise KeyError(f"Unknown head {head!r}. Available: {', '.join(sorted(self.heads))}")
        run_id = run_id or self.store.create_run(goal, mode, origin)
        self.bus.emit("run.start", run_id, None, goal=goal, mode=mode, head=head, origin=origin)
        try:
            if mode == "swarm":
                swarm = await Swarm(self, critic=critic).run(goal, run_id=run_id, origin=origin)
                output, ok = swarm.output, swarm.ok
            else:
                result = await self.run_head(
                    head, goal, run_id=run_id, origin=origin, history=history
                )
                output, ok = result.output, result.ok
        except Exception as exc:
            log.exception("Run %s crashed", run_id)
            output, ok = f"Run failed: {type(exc).__name__}: {exc}", False
        except asyncio.CancelledError:
            self.store.finish_run(run_id, "cancelled", "Cancelled")
            self.bus.emit("run.finish", run_id, None, ok=False, status="cancelled", output="")
            raise
        status = "completed" if ok else "failed"
        self.store.finish_run(run_id, status, output)
        self.bus.emit("run.finish", run_id, None, ok=ok, status=status, output=output[:8000])
        return RunOutcome(run_id, output, ok)

    async def chat(self, session: str, message: str, origin: str = "cli") -> str:
        """One conversational turn with persistent per-session history."""
        text = message.strip()
        if text.startswith("/"):
            command, _, rest = text.partition(" ")
            rest = rest.strip()
            if command == "/help":
                return CHAT_HELP
            if command == "/reset":
                self.store.clear_chat(session)
                return "Conversation cleared."
            if command == "/remember" and rest:
                return f"Saved memory #{self.store.add_memory(rest, source=origin)}."
            if command == "/memories":
                rows = self.store.list_memories(15)
                return "\n".join(f"#{r['id']}: {r['text']}" for r in rows) or "No memories yet."
            if command == "/schedules":
                rows = self.store.list_schedules()
                return "\n".join(f"{r['id']}: {r['name']}" for r in rows) or "No schedules."
            if command in {"/swarm", "/run"} and rest:
                outcome = await self.run(
                    rest, mode="swarm" if command == "/swarm" else "agent", origin=origin
                )
                return outcome.output
            if command not in {"/swarm", "/run", "/remember"}:
                return f"Unknown command {command}.\n\n{CHAT_HELP}"
            return f"Usage: {command} <text>"

        history = [
            Message(row["role"], row["content"]) for row in self.store.chat_history(session, 12)
        ]
        outcome = await self.run(text, origin=origin, history=history)
        self.store.add_chat_message(session, "user", text)
        self.store.add_chat_message(session, "assistant", outcome.output)
        return outcome.output
