"""Multi-head orchestration: plan, execute a task graph in parallel, critique, synthesize.

goal ──> planner ──> task DAG ──> specialist heads (parallel where independent)
                                      │
                          critic ◄────┘  (may send tasks back for revision)
                            │
                      synthesizer ──> final answer
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from agentic.agent import HeadResult
from agentic.llm.jsonutil import extract_json_object

if TYPE_CHECKING:
    from agentic.runtime import Runtime

COORDINATOR_HEADS = {"planner", "critic", "synthesizer"}
MAX_DEP_CONTEXT = 6_000
MAX_REVIEW_CHARS = 5_000
SAFE_ID = re.compile(r"[^a-zA-Z0-9_-]")


@dataclass
class PlannedTask:
    id: str
    head: str
    task: str
    depends_on: list[str] = field(default_factory=list)


@dataclass
class SwarmResult:
    output: str
    ok: bool
    plan: list[PlannedTask]
    results: dict[str, HeadResult]
    revisions: int = 0


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit] + f"\n... [{len(text) - limit} more chars]"


def normalize_plan(raw: Any, workers: set[str], max_tasks: int) -> list[PlannedTask]:
    """Turn untrusted planner JSON into a valid, acyclic task list.

    Unknown heads fall back to the assistant. A task may only depend on tasks
    listed before it, which makes cycles impossible.
    """
    items = raw.get("tasks") if isinstance(raw, dict) else None
    if not isinstance(items, list):
        raise ValueError("plan must contain a 'tasks' list")
    plan: list[PlannedTask] = []
    seen: set[str] = set()
    for index, item in enumerate(items[:max_tasks], 1):
        if not isinstance(item, dict):
            continue
        text = str(item.get("task") or item.get("description") or "").strip()
        if not text:
            continue
        task_id = SAFE_ID.sub("", str(item.get("id") or f"t{index}"))[:20] or f"t{index}"
        while task_id in seen:
            task_id = f"{task_id}_{index}"
        head = str(item.get("head") or item.get("agent") or "assistant").strip().casefold()
        if head not in workers:
            head = "assistant"
        raw_deps = item.get("depends_on") or item.get("deps") or []
        if isinstance(raw_deps, str):
            raw_deps = [raw_deps]
        deps = [str(dep) for dep in raw_deps if str(dep) in seen]
        plan.append(PlannedTask(task_id, head, text, list(dict.fromkeys(deps))))
        seen.add(task_id)
    if not plan:
        raise ValueError("plan contained no usable tasks")
    return plan


class Swarm:
    def __init__(self, runtime: Runtime, critic: bool = True, max_parallel: int | None = None):
        self.runtime = runtime
        self.critic_enabled = critic and "critic" in runtime.heads
        self.max_parallel = max_parallel or runtime.settings.limits.max_parallel

    @property
    def workers(self) -> set[str]:
        return {name for name in self.runtime.heads if name not in COORDINATOR_HEADS}

    async def run(self, goal: str, *, run_id: str, origin: str = "cli") -> SwarmResult:
        bus = self.runtime.bus
        plan = await self.plan(goal, run_id=run_id, origin=origin)
        bus.emit("swarm.plan", run_id, "planner", tasks=[task.__dict__ for task in plan])

        results = await self.execute(goal, plan, run_id=run_id, origin=origin)

        revisions = 0
        limit = self.runtime.settings.limits.max_revisions
        while self.critic_enabled and revisions < limit:
            redo = await self.review(goal, plan, results, run_id=run_id, origin=origin)
            if not redo:
                break
            revisions += 1
            bus.emit("swarm.revision", run_id, "critic", round=revisions, tasks=list(redo))
            by_id = {task.id: task for task in plan}
            slots = asyncio.Semaphore(self.max_parallel)

            async def revise(task_id: str, instructions: str) -> None:
                async with slots:
                    await self._run_task(
                        goal, by_id[task_id], results, run_id, origin, feedback=instructions
                    )

            await asyncio.gather(*[revise(task_id, text) for task_id, text in redo.items()])

        output = await self.synthesize(goal, plan, results, run_id=run_id, origin=origin)
        ok = all(result.ok for result in results.values())
        return SwarmResult(output, ok, plan, results, revisions)

    async def plan(self, goal: str, *, run_id: str, origin: str) -> list[PlannedTask]:
        heads = self.runtime.heads
        catalogue = "\n".join(
            f"- {name}: {heads[name].description}" for name in sorted(self.workers)
        )
        request = (
            f"GOAL:\n{goal}\n\nAVAILABLE HEADS:\n{catalogue}\n\n"
            "Reply with ONLY a JSON object in this shape:\n"
            '{"tasks": [{"id": "t1", "head": "researcher", "task": "self-contained '
            'instructions", "depends_on": []}, {"id": "t2", "head": "writer", "task": "...", '
            '"depends_on": ["t1"]}]}\n'
            f"Use at most {self.runtime.settings.limits.max_tasks} tasks."
        )
        if "planner" in heads:
            for attempt in range(2):
                result = await self.runtime.run_head(
                    "planner", request, run_id=run_id, origin=origin
                )
                raw = extract_json_object(result.output, required_key="tasks")
                try:
                    return normalize_plan(raw, self.workers, self.runtime.settings.limits.max_tasks)
                except ValueError as exc:
                    self.runtime.bus.emit(
                        "swarm.plan_invalid", run_id, "planner", error=str(exc), attempt=attempt + 1
                    )
                    request += f"\n\nYour previous reply was not a valid plan ({exc}). JSON only."
        # A single generalist task is always a valid plan.
        return [PlannedTask("t1", "assistant", goal)]

    async def execute(
        self, goal: str, plan: list[PlannedTask], *, run_id: str, origin: str
    ) -> dict[str, HeadResult]:
        results: dict[str, HeadResult] = {}
        pending = {task.id: task for task in plan}
        running: dict[asyncio.Task, str] = {}
        while pending or running:
            for task_id, task in list(pending.items()):
                if len(running) >= self.max_parallel:
                    break
                if all(dep in results for dep in task.depends_on):
                    del pending[task_id]
                    job = asyncio.create_task(self._run_task(goal, task, results, run_id, origin))
                    running[job] = task_id
            if not running:  # unreachable for a normalized plan; guards against bad input
                for task_id in pending:
                    results[task_id] = HeadResult("assistant", "Skipped: unmet dependencies", False)
                break
            done, _ = await asyncio.wait(running, return_when=asyncio.FIRST_COMPLETED)
            for job in done:
                running.pop(job)
                job.result()
        return results

    async def _run_task(
        self,
        goal: str,
        task: PlannedTask,
        results: dict[str, HeadResult],
        run_id: str,
        origin: str,
        feedback: str = "",
    ) -> None:
        bus = self.runtime.bus
        context_parts = []
        for dep in task.depends_on:
            dep_result = results.get(dep)
            if dep_result:
                status = "" if dep_result.ok else " (INCOMPLETE OR FAILED)"
                context_parts.append(
                    f"### Result of {dep} ({dep_result.head}){status}\n"
                    f"{_clip(dep_result.output, MAX_DEP_CONTEXT)}"
                )
        if feedback and task.id in results:
            context_parts.append(
                f"### Your previous attempt\n{_clip(results[task.id].output, MAX_DEP_CONTEXT)}\n\n"
                f"### Reviewer feedback to address\n{feedback}"
            )
        instructions = (
            f"You are one member of a team working toward this overall goal:\n{goal}\n\n"
            f"YOUR TASK ({task.id}):\n{task.task}"
        )
        bus.emit("task.start", run_id, task.head, task_id=task.id, revision=bool(feedback))
        try:
            result = await self.runtime.run_head(
                task.head,
                instructions,
                run_id=run_id,
                origin=origin,
                context="\n\n".join(context_parts),
            )
        except Exception as exc:  # one failed head must not sink the swarm
            result = HeadResult(task.head, f"Task crashed: {type(exc).__name__}: {exc}", False)
        results[task.id] = result
        bus.emit(
            "task.finish",
            run_id,
            task.head,
            task_id=task.id,
            ok=result.ok,
            output=result.output[:4000],
        )

    def _results_digest(self, plan: list[PlannedTask], results: dict[str, HeadResult]) -> str:
        return "\n\n".join(
            f"## {task.id} - {task.head} - {'ok' if results[task.id].ok else 'INCOMPLETE'}\n"
            f"Task: {task.task}\nResult:\n{_clip(results[task.id].output, MAX_REVIEW_CHARS)}"
            for task in plan
            if task.id in results
        )

    async def review(
        self,
        goal: str,
        plan: list[PlannedTask],
        results: dict[str, HeadResult],
        *,
        run_id: str,
        origin: str,
    ) -> dict[str, str]:
        """Return {task_id: fix instructions} for tasks the critic wants redone."""
        request = (
            f"GOAL:\n{goal}\n\nTEAM RESULTS:\n{self._results_digest(plan, results)}\n\n"
            "Decide whether these results achieve the goal. Reply with ONLY JSON:\n"
            '{"approved": true, "feedback": "short verdict", '
            '"redo": [{"id": "t1", "instructions": "what exactly to fix"}]}\n'
            "Use an empty redo list when approved."
        )
        result = await self.runtime.run_head("critic", request, run_id=run_id, origin=origin)
        verdict = extract_json_object(result.output, required_key="approved") or {}
        approved = verdict.get("approved", True) is not False
        valid_ids = {task.id for task in plan}
        redo: dict[str, str] = {}
        if not approved:
            for item in verdict.get("redo") or []:
                if isinstance(item, dict) and item.get("id") in valid_ids:
                    redo[item["id"]] = str(item.get("instructions") or verdict.get("feedback", ""))
        self.runtime.bus.emit(
            "critic.verdict",
            run_id,
            "critic",
            approved=approved and not redo,
            feedback=str(verdict.get("feedback", ""))[:2000],
            redo=list(redo),
        )
        return redo

    async def synthesize(
        self,
        goal: str,
        plan: list[PlannedTask],
        results: dict[str, HeadResult],
        *,
        run_id: str,
        origin: str,
    ) -> str:
        if len(plan) == 1 or "synthesizer" not in self.runtime.heads:
            return "\n\n".join(results[task.id].output for task in plan if task.id in results)
        request = (
            f"GOAL:\n{goal}\n\nTEAM RESULTS:\n{self._results_digest(plan, results)}\n\n"
            "Write the final answer for the user."
        )
        result = await self.runtime.run_head("synthesizer", request, run_id=run_id, origin=origin)
        return result.output
