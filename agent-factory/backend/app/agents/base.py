from __future__ import annotations

from typing import Any

from ..state import JobStore


class BaseAgent:
    name = "base-agent"

    def __init__(self, store: JobStore) -> None:
        self.store = store

    async def emit(self, job_id: str, phase: str, level: str, message: str, payload: dict[str, Any] | None = None) -> None:
        await self.store.append_event(job_id, self.name, phase, level, message, payload)
