"""Runs scheduled goals while the gateway is serving.

Scheduled runs have origin "schedule:<id>". The approval gate treats them as
unattended: permissions set to "ask" are only allowed when listed in
scheduler.unattended_permissions, everything else is refused.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from agentic.tools.core import next_run_time

if TYPE_CHECKING:
    from agentic.runtime import Runtime

Notifier = Callable[[str, str], Awaitable[None]]
log = logging.getLogger("agentic.scheduler")


class Scheduler:
    def __init__(self, runtime: Runtime, notify: Notifier | None = None):
        self.runtime = runtime
        self.notify = notify
        self._active: dict[str, asyncio.Task] = {}
        self._stopped = asyncio.Event()

    async def tick(self, now: float | None = None) -> list[str]:
        """Start every due schedule that is not already running."""
        now = now or time.time()
        started = []
        for schedule in self.runtime.store.due_schedules(now):
            schedule_id = schedule["id"]
            if schedule_id in self._active:
                continue
            try:
                upcoming = next_run_time(schedule["interval_seconds"], schedule["cron"], now)
            except Exception as exc:
                log.error("Disabling schedule %s: %s", schedule_id, exc)
                self.runtime.store.update_schedule(schedule_id, enabled=0, last_status="invalid")
                continue
            self.runtime.store.update_schedule(schedule_id, next_run=upcoming, last_run=now)
            job = asyncio.create_task(self._run(schedule))
            self._active[schedule_id] = job
            job.add_done_callback(lambda _, key=schedule_id: self._active.pop(key, None))
            started.append(schedule_id)
        return started

    async def _run(self, schedule: dict) -> None:
        outcome = await self.runtime.run(
            schedule["goal"],
            mode=schedule["mode"],
            head=schedule["head"] if schedule["head"] in self.runtime.heads else "assistant",
            origin=f"schedule:{schedule['id']}",
        )
        self.runtime.store.update_schedule(
            schedule["id"], last_status="completed" if outcome.ok else "failed"
        )
        if self.notify and schedule.get("notify"):
            message = f"⏰ {schedule['name']}\n\n{outcome.output}"
            try:
                await self.notify(schedule["notify"], message)
            except Exception:
                log.exception("Could not deliver schedule %s result", schedule["id"])

    async def wait_idle(self) -> None:
        if self._active:
            await asyncio.gather(*self._active.values(), return_exceptions=True)

    async def loop(self) -> None:
        interval = self.runtime.settings.scheduler.poll_seconds
        while not self._stopped.is_set():
            try:
                await self.tick()
            except Exception:
                log.exception("Scheduler tick failed")
            try:
                await asyncio.wait_for(self._stopped.wait(), interval)
            except asyncio.TimeoutError:
                pass

    def stop(self) -> None:
        self._stopped.set()
        for job in self._active.values():
            job.cancel()
