"""The gateway: an always-on local server for the dashboard, API, channels, and scheduler.

Binds to 127.0.0.1 by default. When the token variable (AGENTIC_TOKEN) is set,
every API call needs `Authorization: Bearer <token>` (or `?token=` for the
event stream). Requests from other web origins and unexpected Host headers
are refused, which blocks drive-by requests and DNS rebinding from websites.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from agentic import __version__
from agentic.approvals import ApprovalRequest, PendingApprovals
from agentic.config import Settings
from agentic.cron import CronSchedule
from agentic.events import Event
from agentic.runtime import Runtime
from agentic.scheduler import Scheduler
from agentic.tools.core import next_run_time

DASHBOARD = Path(__file__).resolve().parent / "static" / "dashboard.html"
LOOPBACK = {"127.0.0.1", "localhost", "::1"}
log = logging.getLogger("agentic.gateway")


class RunRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=20_000)
    mode: Literal["agent", "swarm"] = "agent"
    head: str = "assistant"
    critic: bool = True


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20_000)
    session: str = Field(default="dashboard", max_length=120)


class ApprovalDecision(BaseModel):
    approve: bool
    remember_for_run: bool = False


class MemoryRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4_000)
    tags: list[str] = Field(default_factory=list, max_length=8)


class ScheduleRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=4_000)
    name: str | None = Field(default=None, max_length=120)
    every_minutes: int | None = Field(default=None, ge=1, le=525_600)
    cron: str | None = None
    mode: Literal["agent", "swarm"] = "agent"
    head: str = "assistant"


def create_app(
    settings: Settings,
    *,
    runtime: Runtime | None = None,
    background: bool = True,
) -> FastAPI:
    approvals = PendingApprovals()
    runtime = runtime or Runtime(settings)
    runtime.gate.approver = approvals
    token = os.getenv(settings.gateway.token_env) or ""
    tasks: dict[str, asyncio.Task] = {}
    listeners: set[tuple[asyncio.Queue, asyncio.AbstractEventLoop]] = set()
    state: dict[str, object] = {"telegram": "disabled"}
    pending_meta: dict[str, ApprovalRequest] = {}
    approval_hooks = []

    def on_approval(request: ApprovalRequest) -> None:
        pending_meta[request.id] = request
        runtime.bus.emit(
            "approval.requested",
            request.run_id,
            request.agent,
            id=request.id,
            tool=request.tool,
            permission=request.permission,
            args=request.args,
            summary=request.summary(),
        )
        for hook in approval_hooks:
            hook(request)

    approvals.on_request = on_approval

    def broadcast(event: Event) -> None:
        for queue, loop in list(listeners):
            loop.call_soon_threadsafe(queue.put_nowait, event)

    runtime.bus.subscribe(broadcast)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        background_jobs: list[asyncio.Task] = []
        scheduler = None
        telegram = None
        if background:
            await runtime.start_mcp()
            if settings.channels.telegram.enabled:
                from agentic.channels.telegram import TelegramChannel

                try:
                    telegram = TelegramChannel(runtime, settings.channels.telegram, approvals)
                    approval_hooks.append(telegram.on_approval_request)
                    background_jobs.append(asyncio.create_task(telegram.loop()))
                    state["telegram"] = "online"
                except RuntimeError as exc:
                    state["telegram"] = f"error: {exc}"
                    log.error("%s", exc)
            if settings.scheduler.enabled:
                scheduler = Scheduler(runtime, notify=telegram.notify if telegram else None)
                background_jobs.append(asyncio.create_task(scheduler.loop()))
        app.state.scheduler = scheduler
        try:
            yield
        finally:
            if scheduler:
                scheduler.stop()
            if telegram:
                telegram.stop()
            for job in [*background_jobs, *tasks.values()]:
                job.cancel()
            await runtime.aclose()

    app = FastAPI(title="Agentic Gateway", version=__version__, lifespan=lifespan)
    app.state.runtime = runtime
    app.state.approvals = approvals

    @app.middleware("http")
    async def same_origin_only(request: Request, call_next):
        host_header = request.headers.get("host", "")
        hostname = urlparse(f"//{host_header}").hostname or ""
        if settings.gateway.host in LOOPBACK and hostname not in LOOPBACK | {"testserver"}:
            return JSONResponse({"detail": "Unexpected Host header"}, status_code=403)
        origin = request.headers.get("origin")
        if origin and urlparse(origin).netloc != host_header:
            return JSONResponse({"detail": "Cross-origin requests are not allowed"}, 403)
        return await call_next(request)

    def require_token(request: Request) -> None:
        if not token:
            return
        supplied = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
        supplied = supplied or request.query_params.get("token", "")
        if not secrets.compare_digest(supplied.encode(), token.encode()):
            raise HTTPException(401, "Missing or invalid token")

    api = [Depends(require_token)]

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def dashboard() -> str:
        return DASHBOARD.read_text(encoding="utf-8")

    @app.get("/api/status", dependencies=api)
    async def status() -> dict:
        provider = settings.provider()
        return {
            "version": __version__,
            "provider": settings.default_provider,
            "model": provider.model,
            "provider_type": provider.type,
            "heads": len(runtime.heads),
            "tools": len(runtime.tools.all()),
            "mcp_servers": [client.name for client in runtime.mcp_clients],
            "mcp_errors": runtime.mcp_errors,
            "telegram": state["telegram"],
            "active_runs": sorted(tasks),
            "auth": bool(token),
            "workspace": str(settings.workspace_path),
        }

    @app.get("/api/heads", dependencies=api)
    async def heads() -> list[dict]:
        return [
            {
                "name": h.name,
                "description": h.description,
                "tools": list(h.tools),
                "provider": h.provider or settings.default_provider,
            }
            for h in runtime.heads.values()
        ]

    @app.get("/api/tools", dependencies=api)
    async def tools() -> list[dict]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "permission": t.permission,
                "policy": runtime.gate.mode_for(t.permission),
            }
            for t in runtime.tools.all()
        ]

    @app.get("/api/runs", dependencies=api)
    async def list_runs(limit: int = 30) -> list[dict]:
        return runtime.store.list_runs(min(max(limit, 1), 200))

    @app.post("/api/runs", dependencies=api, status_code=202)
    async def create_run(body: RunRequest) -> dict:
        if body.head not in runtime.heads:
            raise HTTPException(400, f"Unknown head {body.head!r}")
        run_id = runtime.store.create_run(body.goal, body.mode, "dashboard")
        job = asyncio.create_task(
            runtime.run(
                body.goal,
                mode=body.mode,
                head=body.head,
                origin="dashboard",
                critic=body.critic,
                run_id=run_id,
            )
        )
        tasks[run_id] = job
        job.add_done_callback(lambda _: tasks.pop(run_id, None))
        return {"run_id": run_id}

    @app.get("/api/runs/{run_id}", dependencies=api)
    async def get_run(run_id: str) -> dict:
        run = runtime.store.get_run(run_id)
        if run is None:
            raise HTTPException(404, "Run not found")
        return {**run, "events": runtime.store.events(run_id)}

    @app.post("/api/runs/{run_id}/cancel", dependencies=api)
    async def cancel_run(run_id: str) -> dict:
        job = tasks.get(run_id)
        if job is None:
            raise HTTPException(404, "Run is not active")
        job.cancel()
        return {"cancelled": True}

    @app.get("/api/approvals", dependencies=api)
    async def list_approvals() -> list[dict]:
        return [
            {
                "id": r.id,
                "tool": r.tool,
                "permission": r.permission,
                "args": r.args,
                "agent": r.agent,
                "run_id": r.run_id,
                "summary": r.summary(),
            }
            for r in approvals.list()
        ]

    @app.post("/api/approvals/{request_id}", dependencies=api)
    async def decide(request_id: str, body: ApprovalDecision) -> dict:
        request = pending_meta.pop(request_id, None)
        if body.approve and body.remember_for_run and request:
            runtime.gate.grant_for_run(request.run_id, request.tool)
        if not approvals.resolve(request_id, body.approve):
            raise HTTPException(404, "No pending approval with that id")
        runtime.bus.emit(
            "approval.resolved",
            request.run_id if request else "-",
            None,
            id=request_id,
            approved=body.approve,
        )
        return {"ok": True}

    @app.post("/api/chat", dependencies=api)
    async def chat(body: ChatRequest) -> dict:
        reply = await runtime.chat(f"dashboard:{body.session}", body.message, origin="dashboard")
        return {"reply": reply}

    @app.get("/api/memories", dependencies=api)
    async def memories(q: str = "", limit: int = 30) -> list[dict]:
        limit = min(max(limit, 1), 200)
        return runtime.store.search_memories(q, limit) if q else runtime.store.list_memories(limit)

    @app.post("/api/memories", dependencies=api, status_code=201)
    async def add_memory(body: MemoryRequest) -> dict:
        return {"id": runtime.store.add_memory(body.text, body.tags, source="dashboard")}

    @app.delete("/api/memories/{memory_id}", dependencies=api)
    async def delete_memory(memory_id: int) -> dict:
        if not runtime.store.delete_memory(memory_id):
            raise HTTPException(404, "Memory not found")
        return {"ok": True}

    @app.get("/api/schedules", dependencies=api)
    async def schedules() -> list[dict]:
        return runtime.store.list_schedules()

    @app.post("/api/schedules", dependencies=api, status_code=201)
    async def add_schedule(body: ScheduleRequest) -> dict:
        if bool(body.every_minutes) == bool(body.cron):
            raise HTTPException(400, "Provide exactly one of every_minutes or cron")
        if body.head not in runtime.heads:
            raise HTTPException(400, f"Unknown head {body.head!r}")
        if body.cron:
            try:
                CronSchedule.parse(body.cron)
            except ValueError as exc:
                raise HTTPException(400, str(exc)) from exc
        interval = body.every_minutes * 60 if body.every_minutes else None
        schedule_id = runtime.store.add_schedule(
            name=body.name or body.goal[:60],
            goal=body.goal,
            mode=body.mode,
            head=body.head,
            interval_seconds=interval,
            cron=body.cron,
            notify=None,
            next_run=next_run_time(interval, body.cron, time.time()),
        )
        return {"id": schedule_id}

    @app.delete("/api/schedules/{schedule_id}", dependencies=api)
    async def delete_schedule(schedule_id: str) -> dict:
        if not runtime.store.delete_schedule(schedule_id):
            raise HTTPException(404, "Schedule not found")
        return {"ok": True}

    @app.get("/api/stream", dependencies=api)
    async def stream(request: Request) -> StreamingResponse:
        queue: asyncio.Queue = asyncio.Queue(maxsize=2_000)
        entry = (queue, asyncio.get_running_loop())
        listeners.add(entry)

        async def events():
            try:
                yield "retry: 2000\n\n"
                while not await request.is_disconnected():
                    try:
                        event = await asyncio.wait_for(queue.get(), 15)
                    except asyncio.TimeoutError:
                        yield ": keep-alive\n\n"
                        continue
                    yield f"data: {json.dumps(event.to_dict(), default=str)}\n\n"
            finally:
                listeners.discard(entry)

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return app


def serve(settings: Settings, host: str | None = None, port: int | None = None) -> None:
    import uvicorn

    bind_host = host or settings.gateway.host
    if bind_host not in LOOPBACK and not os.getenv(settings.gateway.token_env):
        raise SystemExit(
            f"Refusing to listen on {bind_host} without a token. "
            f"Set {settings.gateway.token_env} first."
        )
    if bind_host != settings.gateway.host:
        settings.gateway.host = bind_host
    uvicorn.run(
        create_app(settings), host=bind_host, port=port or settings.gateway.port, log_level="info"
    )
