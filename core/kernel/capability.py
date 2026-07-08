"""Capability contracts for the Veraxis kernel."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


@dataclass
class CapabilityRequest:
    """Structured request passed to a capability."""

    capability_name: str
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    request_id: str = field(default_factory=lambda: uuid4().hex)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CapabilityResponse:
    """Structured response returned by a capability."""

    success: bool
    result: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class Capability(ABC):
    """Abstract base contract for all kernel capabilities."""

    name = ""
    version = "1.0.0"
    description = ""

    @abstractmethod
    def execute(self, request: CapabilityRequest) -> CapabilityResponse:
        """Execute the capability with a structured request."""
