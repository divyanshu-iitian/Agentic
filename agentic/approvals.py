"""Human-in-the-loop approval for consequential tool calls.

Each tool declares a permission tier. The policy maps tiers to auto, ask, or
deny. "ask" is resolved by whichever approver the current surface installed:
a terminal prompt, the dashboard, or a chat channel. Without an approver,
"ask" means deny, so unattended runs can never silently escalate.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from agentic.config import PermissionPolicy


@dataclass
class ApprovalRequest:
    tool: str
    permission: str
    args: dict[str, Any]
    run_id: str
    agent: str
    origin: str = "cli"
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    def summary(self, limit: int = 600) -> str:
        rendered = json.dumps(self.args, ensure_ascii=False)
        if len(rendered) > limit:
            rendered = rendered[:limit] + "..."
        return f"{self.agent} wants to run {self.tool} ({self.permission}): {rendered}"


Approver = Callable[[ApprovalRequest], Awaitable[bool]]


class ApprovalGate:
    def __init__(
        self,
        policy: PermissionPolicy,
        approver: Approver | None = None,
        timeout: float = 300,
        overrides: dict[str, str] | None = None,
        unattended: set[str] | None = None,
    ):
        self.policy = policy
        self.approver = approver
        self.timeout = timeout
        self.overrides = dict(overrides or {})
        # Permissions that scheduled runs may use where the policy says "ask".
        self.unattended = set(unattended or ())
        # (run_id, tool) pairs the user approved for the rest of a run.
        self.session_grants: set[tuple[str, str]] = set()

    def mode_for(self, permission: str) -> str:
        if permission in self.overrides:
            return self.overrides[permission]
        return getattr(self.policy, permission, "ask")

    async def check(self, request: ApprovalRequest) -> tuple[bool, str]:
        mode = self.mode_for(request.permission)
        if mode == "auto" or (request.run_id, request.tool) in self.session_grants:
            return True, ""
        if mode == "deny":
            return False, f"Permission '{request.permission}' is denied by policy."
        if request.origin.startswith("schedule:"):
            if request.permission in self.unattended:
                return True, ""
            return False, (
                f"Scheduled runs cannot ask for '{request.permission}' approval. Add it to "
                "scheduler.unattended_permissions or set it to auto."
            )
        if self.approver is None:
            return False, (
                f"{request.tool} needs '{request.permission}' approval and no approver is "
                "attached. Change the permissions policy or run interactively."
            )
        try:
            approved = await asyncio.wait_for(self.approver(request), self.timeout)
        except asyncio.TimeoutError:
            return False, "Approval timed out."
        return (True, "") if approved else (False, "The user declined this action.")

    def grant_for_run(self, run_id: str, tool: str) -> None:
        self.session_grants.add((run_id, tool))


class PendingApprovals:
    """Approval requests waiting on a remote decision (dashboard or chat)."""

    def __init__(self, on_request: Callable[[ApprovalRequest], None] | None = None):
        self.on_request = on_request
        self._pending: dict[
            str, tuple[ApprovalRequest, asyncio.Future, asyncio.AbstractEventLoop]
        ] = {}

    async def __call__(self, request: ApprovalRequest) -> bool:
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        self._pending[request.id] = (request, future, loop)
        if self.on_request:
            self.on_request(request)
        try:
            return await future
        finally:
            self._pending.pop(request.id, None)

    def list(self) -> list[ApprovalRequest]:
        return [request for request, _, _ in self._pending.values()]

    def resolve(self, request_id: str, approved: bool) -> bool:
        entry = self._pending.get(request_id)
        if entry is None:
            return False
        _, future, loop = entry

        def _set() -> None:
            if not future.done():
                future.set_result(approved)

        loop.call_soon_threadsafe(_set)
        return True
