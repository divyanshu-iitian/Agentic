"""Tests for planning, parallel execution, critic revisions, and synthesis."""

import asyncio
import json
import threading
import time

from agentic.llm.scripted import ScriptedProvider
from agentic.swarm import normalize_plan

PLAN = {
    "tasks": [
        {"id": "t1", "head": "researcher", "task": "find facts", "depends_on": []},
        {"id": "t2", "head": "coder", "task": "write code", "depends_on": []},
        {"id": "t3", "head": "writer", "task": "write report", "depends_on": ["t1", "t2"]},
    ]
}


class TeamProvider:
    """Answers as whichever head is speaking, tracking concurrency."""

    def __init__(self, verdicts=None, plan=PLAN):
        self.plan = plan
        self.verdicts = list(verdicts or [{"approved": True, "feedback": "good", "redo": []}])
        self.active = 0
        self.max_active = 0
        self.seen: list[tuple[str, str]] = []
        self._lock = threading.Lock()

    def __call__(self, messages, tools):
        system, user = messages[0].content, messages[-1].content
        head = system.split(" head", 1)[0].removeprefix("You are the ").strip().casefold()
        with self._lock:
            self.seen.append((head, user))
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            if head == "planner":
                return json.dumps(self.plan)
            if head == "critic":
                verdict = self.verdicts.pop(0) if self.verdicts else {"approved": True}
                return json.dumps(verdict)
            if head == "synthesizer":
                return "FINAL: " + " | ".join(
                    line for line in user.splitlines() if line.startswith("output-")
                )
            time.sleep(0.15)  # long enough for parallel heads to overlap
            return f"output-{head}"
        finally:
            with self._lock:
                self.active -= 1


def run_swarm(runtime, goal="build a thing"):
    return asyncio.run(runtime.run(goal, mode="swarm"))


def test_swarm_runs_independent_tasks_in_parallel(make_runtime) -> None:
    team = TeamProvider()
    runtime = make_runtime(ScriptedProvider(responder=team))
    outcome = run_swarm(runtime)

    assert outcome.ok
    assert team.max_active >= 2, "t1 and t2 should overlap"
    writer_prompt = next(user for head, user in team.seen if head == "writer")
    assert "Result of t1 (researcher)" in writer_prompt and "output-researcher" in writer_prompt
    assert "Result of t2 (coder)" in writer_prompt
    assert outcome.output == "FINAL: output-researcher | output-coder | output-writer"

    order = [
        (row["type"], row["data"].get("task_id"))
        for row in runtime.store.events(outcome.run_id)
        if row["type"] in {"task.start", "task.finish"}
    ]
    assert order.index(("task.start", "t3")) > order.index(("task.finish", "t1"))
    assert order.index(("task.start", "t3")) > order.index(("task.finish", "t2"))


def test_max_parallel_one_serializes_heads(make_runtime) -> None:
    team = TeamProvider()
    runtime = make_runtime(ScriptedProvider(responder=team), limits={"max_parallel": 1})
    run_swarm(runtime)
    assert team.max_active == 1


def test_critic_sends_a_task_back_once(make_runtime) -> None:
    team = TeamProvider(
        verdicts=[
            {
                "approved": False,
                "feedback": "missing sources",
                "redo": [{"id": "t1", "instructions": "add sources"}],
            },
            {
                "approved": False,
                "feedback": "still bad",
                "redo": [{"id": "t1", "instructions": "again"}],
            },
        ]
    )
    runtime = make_runtime(ScriptedProvider(responder=team), limits={"max_revisions": 1})
    outcome = run_swarm(runtime)

    researcher_prompts = [user for head, user in team.seen if head == "researcher"]
    assert len(researcher_prompts) == 2
    assert "Reviewer feedback to address\nadd sources" in researcher_prompts[1]
    assert "Your previous attempt\noutput-researcher" in researcher_prompts[1]
    types = [row["type"] for row in runtime.store.events(outcome.run_id)]
    assert types.count("swarm.revision") == 1
    assert types.count("critic.verdict") == 1


def test_no_critic_flag_skips_review(make_runtime) -> None:
    team = TeamProvider()
    runtime = make_runtime(ScriptedProvider(responder=team))
    asyncio.run(runtime.run("goal", mode="swarm", critic=False))
    assert all(head != "critic" for head, _ in team.seen)


def test_invalid_plans_fall_back_to_the_assistant(make_runtime) -> None:
    calls = []

    def responder(messages, tools):
        calls.append(messages[0].content[:40])
        if messages[0].content.startswith("You are the Planner"):
            return "I think we should just do it."
        return "assistant did everything"

    runtime = make_runtime(ScriptedProvider(responder=responder))
    outcome = asyncio.run(runtime.run("goal", mode="swarm", critic=False))

    assert outcome.output == "assistant did everything"
    types = [row["type"] for row in runtime.store.events(outcome.run_id)]
    assert types.count("swarm.plan_invalid") == 2


def test_failed_head_does_not_sink_the_swarm(make_runtime) -> None:
    team = TeamProvider()

    def responder(messages, tools):
        if messages[0].content.startswith("You are the Coder"):
            raise RuntimeError("model crashed")
        return team(messages, tools)

    runtime = make_runtime(ScriptedProvider(responder=responder))
    outcome = run_swarm(runtime)
    assert not outcome.ok
    finishes = {
        row["data"]["task_id"]: row["data"]["ok"]
        for row in runtime.store.events(outcome.run_id)
        if row["type"] == "task.finish"
    }
    assert finishes == {"t1": True, "t2": False, "t3": True}


def test_normalize_plan_repairs_untrusted_plans() -> None:
    raw = {
        "tasks": [
            {"id": "a", "head": "wizard", "task": "one", "depends_on": ["b"]},
            {"id": "b", "head": "Researcher", "task": "two", "depends_on": ["a", "b", "zzz"]},
            {"id": "b", "head": "coder", "task": "three", "depends_on": "a"},
            {"id": "c", "head": "coder", "task": ""},
            "garbage",
        ]
    }
    plan = normalize_plan(raw, {"assistant", "researcher", "coder"}, max_tasks=8)
    assert [(t.id, t.head, t.depends_on) for t in plan] == [
        ("a", "assistant", []),  # forward reference dropped, unknown head replaced
        ("b", "researcher", ["a"]),  # self and unknown references dropped
        ("b_3", "coder", ["a"]),  # duplicate id renamed
    ]


def test_normalize_plan_caps_task_count() -> None:
    raw = {"tasks": [{"head": "assistant", "task": f"step {i}"} for i in range(20)]}
    assert len(normalize_plan(raw, {"assistant"}, max_tasks=4)) == 4


def test_every_builtin_head_loads() -> None:
    from agentic.heads import BUILTIN_DIR, load_heads

    heads = load_heads()
    assert len(heads) == len(list(BUILTIN_DIR.glob("*.md")))
    assert {"assistant", "planner", "critic", "synthesizer", "operator"} <= set(heads)
