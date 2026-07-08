"""Minimal deterministic event primitives for the Veraxis kernel."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable
from uuid import uuid4


@dataclass
class Event:
    """Kernel event payload."""

    type: str
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid4().hex)
    created_at: datetime = field(default_factory=datetime.utcnow)


class EventBus:
    """In-memory synchronous event bus."""

    def __init__(self) -> None:
        self._events: list[Event] = []
        self._subscribers: dict[str, list[Callable[[Event], None]]] = defaultdict(list)

    @property
    def event_count(self) -> int:
        return len(self._events)

    def publish(self, event: Event) -> Event:
        self._events.append(event)
        for handler in list(self._subscribers.get(event.type, [])):
            try:
                handler(event)
            except Exception:
                continue
        return event

    def subscribe(self, event_type: str, handler: Callable[[Event], None]) -> None:
        self._subscribers[event_type].append(handler)

    def get_events(self, event_type: str | None = None, limit: int = 100) -> list[Event]:
        effective_limit = max(int(limit or 0), 0)
        if event_type:
            events = [event for event in self._events if event.type == event_type]
        else:
            events = list(self._events)
        if effective_limit == 0:
            return []
        return events[-effective_limit:]
