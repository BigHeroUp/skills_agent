"""Kernel runtime foundation for Veraxis."""

from .builtin_capabilities import HealthCheckCapability
from .capability import Capability, CapabilityRequest, CapabilityResponse
from .errors import (
    CapabilityExecutionError,
    CapabilityNotFoundError,
    DuplicateCapabilityError,
    KernelError,
)
from .events import Event, EventBus
from .kernel import VeraxisKernel
from .memory import KernelMemory
from .registry import CapabilityRegistry

__all__ = [
    "Capability",
    "CapabilityExecutionError",
    "CapabilityNotFoundError",
    "CapabilityRegistry",
    "CapabilityRequest",
    "CapabilityResponse",
    "DuplicateCapabilityError",
    "Event",
    "EventBus",
    "HealthCheckCapability",
    "KernelError",
    "KernelMemory",
    "VeraxisKernel",
]
