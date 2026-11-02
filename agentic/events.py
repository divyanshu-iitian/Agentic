"""In-process event bus. Every step of every run is an event.

Events are persisted to the store and fanned out to subscribers: the CLI
renderer, the dashboard's SSE stream, and chat channels.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Any

from agentic.store import Store

log = logging.getLogger("agentic.events")


@dataclass
class Event:
    type: str
    run_id: str
    agent: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time.time)
    id: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


Subscriber = Callable[[Event], None]


class EventBus:
    def __init__(self, store: Store | None = None):
        self.store = store
        self._subscribers: list[Subscriber] = []

    def subscribe(self, callback: Subscriber) -> Callable[[], None]:
        self._subscribers.append(callback)
        return lambda: self._subscribers.remove(callback)

    def emit(self, kind: str, run_id: str, agent: str | None = None, **data: Any) -> Event:
        event = Event(kind, run_id, agent, data)
        if self.store is not None:
            event.id = self.store.add_event(run_id, event.ts, kind, agent, data)
        for callback in list(self._subscribers):
            try:
                callback(event)
            except Exception:  # a broken subscriber must never break a run
                log.exception("Event subscriber failed")
        return event
