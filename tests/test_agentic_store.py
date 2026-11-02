"""Tests for persistence, cron parsing, scheduling, and MCP."""

import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path

import pytest

from agentic.config import MCPServerConfig
from agentic.cron import CronSchedule
from agentic.llm.scripted import ScriptedProvider, tool_reply
from agentic.scheduler import Scheduler
from agentic.store import Store
from agentic.tools.base import ToolError
from agentic.tools.mcp import MCPClient, mcp_tools

FAKE_SERVER = str(Path(__file__).parent / "fixtures" / "fake_mcp_server.py")


def test_memory_search_ranks_and_dedupes(tmp_path) -> None:
    store = Store(tmp_path / "db.sqlite")
    first = store.add_memory("User prefers dark mode in every editor")
    assert store.add_memory("User prefers dark mode in every editor") == first
    store.add_memory("The deploy target is the atlas server", ["infra"])
    store.add_memory("Coffee order: flat white")

    hits = store.search_memories("which server do we deploy to?")
    assert hits[0]["text"] == "The deploy target is the atlas server"
    assert store.search_memories("infra")[0]["tags"] == "infra"
    assert store.search_memories("zebra unicorn") == []
    assert store.delete_memory(first) and not store.search_memories("dark mode")
    store.close()


def test_chat_history_is_ordered_and_bounded(tmp_path) -> None:
    store = Store(tmp_path / "db.sqlite")
    for i in range(6):
        store.add_chat_message("s", "user", f"m{i}")
    assert [row["content"] for row in store.chat_history("s", 3)] == ["m3", "m4", "m5"]
    store.close()


@pytest.mark.parametrize(
    ("expression", "after", "expected"),
    [
        ("*/15 * * * *", datetime(2026, 1, 1, 10, 7), datetime(2026, 1, 1, 10, 15)),
        ("0 9 * * 1-5", datetime(2026, 1, 2, 10, 0), datetime(2026, 1, 5, 9, 0)),  # Fri → Mon
        ("30 23 31 12 *", datetime(2026, 6, 1), datetime(2026, 12, 31, 23, 30)),
        ("0 0 1 * 0", datetime(2026, 1, 1, 0, 0), datetime(2026, 1, 4, 0, 0)),  # day OR Sunday
        ("0 12 * * 7", datetime(2026, 1, 1), datetime(2026, 1, 4, 12, 0)),  # 7 is Sunday
        ("5,10 8-9 * * *", datetime(2026, 1, 1, 8, 10), datetime(2026, 1, 1, 9, 5)),
    ],
)
def test_cron_next_after(expression, after, expected) -> None:
    assert CronSchedule.parse(expression).next_after(after) == expected


@pytest.mark.parametrize(
    "bad", ["* * * *", "61 * * * *", "*/0 * * * *", "a b c d e", "5-1 * * * *"]
)
def test_cron_rejects_bad_expressions(bad) -> None:
    with pytest.raises(ValueError):
        CronSchedule.parse(bad)


def test_scheduler_runs_due_jobs_unattended(make_runtime) -> None:
    provider = ScriptedProvider(
        [tool_reply("write_file", path="report.md", content="x"), "Could not write; no approval."]
    )

    async def approver(request):
        raise AssertionError("scheduled runs must not prompt")

    runtime = make_runtime(provider, approver=approver)
    store = runtime.store
    schedule_id = store.add_schedule(
        name="nightly",
        goal="write the report",
        mode="agent",
        head="assistant",
        interval_seconds=3600,
        cron=None,
        notify="telegram:42",
        next_run=time.time() - 1,
    )
    delivered = []

    async def notify(target, text):
        delivered.append((target, text))

    async def scenario():
        scheduler = Scheduler(runtime, notify=notify)
        assert await scheduler.tick() == [schedule_id]
        assert await scheduler.tick() == []  # next_run moved forward
        await scheduler.wait_idle()

    asyncio.run(scenario())
    schedule = store.list_schedules()[0]
    assert schedule["last_status"] == "completed"
    assert schedule["next_run"] > time.time() + 3000
    assert not (runtime.settings.workspace_path / "report.md").exists()
    assert delivered == [("telegram:42", "⏰ nightly\n\nCould not write; no approval.")]
    run = store.list_runs()[0]
    assert run["origin"] == f"schedule:{schedule_id}"
    result = [e for e in store.events(run["id"]) if e["type"] == "tool.result"][0]
    assert "unattended_permissions" in result["data"]["output"]


def test_mcp_client_lists_and_calls_tools() -> None:
    client = MCPClient("fake", MCPServerConfig(command=sys.executable, args=[FAKE_SERVER]), 10)
    try:
        client.start()
        assert client.server_info["name"] == "fake"
        tools = {tool.name: tool for tool in mcp_tools(client)}
        assert set(tools) == {"mcp__fake__echo", "mcp__fake__explode"}
        echo = tools["mcp__fake__echo"]
        assert echo.permission == "execute" and echo.parameters["required"] == ["text"]
        assert echo.handler({"text": "ping"}, None) == "ping"
        with pytest.raises(ToolError, match="boom"):
            tools["mcp__fake__explode"].handler({}, None)
    finally:
        client.close()


def test_runtime_registers_mcp_tools_and_reports_failures(make_runtime) -> None:
    runtime = make_runtime(
        ScriptedProvider(),
        mcp_servers={
            "fake": {"command": sys.executable, "args": [FAKE_SERVER], "permission": "read"},
            "broken": {"command": "definitely-not-a-real-binary-xyz"},
        },
    )
    asyncio.run(runtime.start_mcp())
    assert runtime.tools.get("mcp__fake__echo").permission == "read"
    assert "broken" in runtime.mcp_errors
    assert [t.name for t in runtime.tools.select(["mcp__*"])] == [
        "mcp__fake__echo",
        "mcp__fake__explode",
    ]
