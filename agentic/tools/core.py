"""Tools that use the runtime itself: memory, scheduling, and delegation."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from agentic.cron import CronSchedule
from agentic.tools.base import Tool, ToolContext, ToolError, schema


def remember(args: dict[str, Any], ctx: ToolContext) -> str:
    tags = [str(tag) for tag in args.get("tags", [])][:8]
    memory_id = ctx.runtime.store.add_memory(args["text"], tags, source=f"agent:{ctx.agent}")
    return f"Stored memory #{memory_id}"


def recall(args: dict[str, Any], ctx: ToolContext) -> str:
    rows = ctx.runtime.store.search_memories(args["query"], int(args.get("limit", 5)))
    if not rows:
        return "No matching memories."
    return "\n".join(f"#{row['id']}: {row['text']}" for row in rows)


def next_run_time(interval_seconds: int | None, cron: str | None, now: float) -> float:
    if cron:
        return CronSchedule.parse(cron).next_after(datetime.fromtimestamp(now)).timestamp()
    if interval_seconds:
        return now + interval_seconds
    raise ToolError("Provide every_minutes or cron")


def schedule_task(args: dict[str, Any], ctx: ToolContext) -> str:
    every = args.get("every_minutes")
    cron = args.get("cron")
    if bool(every) == bool(cron):
        raise ToolError("Provide exactly one of every_minutes or cron")
    if cron:
        try:
            CronSchedule.parse(cron)
        except ValueError as exc:
            raise ToolError(str(exc)) from exc
    interval = int(every) * 60 if every else None
    mode = args.get("mode", "agent")
    heads = ctx.runtime.heads
    head = args.get("head", "assistant")
    if head not in heads:
        raise ToolError(f"Unknown head '{head}'. Available: {', '.join(sorted(heads))}")
    schedule_id = ctx.runtime.store.add_schedule(
        name=args.get("name") or args["goal"][:60],
        goal=args["goal"],
        mode=mode,
        head=head,
        interval_seconds=interval,
        cron=cron,
        notify=ctx.origin if ctx.origin.startswith("telegram:") else None,
        next_run=next_run_time(interval, cron, time.time()),
    )
    when = f"every {every} minutes" if every else f"on cron '{cron}'"
    return f"Scheduled {schedule_id} to run {when}. Runs happen while the gateway is serving."


def list_schedules(args: dict[str, Any], ctx: ToolContext) -> str:
    rows = ctx.runtime.store.list_schedules()
    if not rows:
        return "No schedules."
    return "\n".join(
        f"{row['id']}: {row['name']} | "
        + (f"every {row['interval_seconds'] // 60}m" if row["interval_seconds"] else row["cron"])
        + f" | next {datetime.fromtimestamp(row['next_run']):%Y-%m-%d %H:%M}"
        + ("" if row["enabled"] else " | disabled")
        for row in rows
    )


async def delegate(args: dict[str, Any], ctx: ToolContext) -> str:
    runtime = ctx.runtime
    if ctx.depth >= runtime.settings.limits.max_delegation_depth:
        raise ToolError("Delegation depth limit reached; finish this part yourself")
    head = args["head"]
    if head not in runtime.heads:
        raise ToolError(f"Unknown head '{head}'. Available: {', '.join(sorted(runtime.heads))}")
    if head == ctx.agent:
        raise ToolError("A head cannot delegate to itself")
    result = await runtime.run_head(
        head,
        args["task"],
        run_id=ctx.run_id,
        origin=ctx.origin,
        depth=ctx.depth + 1,
        context=args.get("context", ""),
    )
    status = "completed" if result.ok else "incomplete"
    return f"[{head} {status}]\n{result.output}"


def core_tools() -> list[Tool]:
    return [
        Tool(
            "remember",
            "Save a durable fact or user preference to long-term memory.",
            schema(
                {
                    "text": {"type": "string", "maxLength": 4000},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                ["text"],
            ),
            "memory",
            remember,
        ),
        Tool(
            "recall",
            "Search long-term memory for relevant facts and preferences.",
            schema(
                {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 20},
                },
                ["query"],
            ),
            "memory",
            recall,
        ),
        Tool(
            "schedule_task",
            "Schedule a goal to run automatically, every N minutes or on a cron expression "
            "(minute hour day month weekday). Use for recurring automation.",
            schema(
                {
                    "goal": {"type": "string", "maxLength": 4000},
                    "every_minutes": {"type": "integer", "minimum": 1, "maximum": 525_600},
                    "cron": {"type": "string"},
                    "mode": {"type": "string", "enum": ["agent", "swarm"]},
                    "head": {"type": "string"},
                    "name": {"type": "string", "maxLength": 120},
                },
                ["goal"],
            ),
            "schedule",
            schedule_task,
        ),
        Tool(
            "list_schedules",
            "List scheduled automations.",
            schema({}),
            "read",
            list_schedules,
        ),
        Tool(
            "delegate",
            "Hand a self-contained subtask to another specialist head and get its answer.",
            schema(
                {
                    "head": {"type": "string"},
                    "task": {"type": "string", "maxLength": 8000},
                    "context": {"type": "string", "maxLength": 16000},
                },
                ["head", "task"],
            ),
            "read",
            delegate,
            blocking=False,
            timeout=3600,
        ),
    ]
