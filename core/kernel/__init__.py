"""Kernel runtime foundation for Veraxis."""

from .builtin_capabilities import HealthCheckCapability
from .bootstrap import create_default_kernel
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
from .provider import CapabilityProvider
from .registry import CapabilityRegistry

__all__ = [
    "Capability",
    "CapabilityProvider",
    "CapabilityExecutionError",
    "CapabilityNotFoundError",
    "CapabilityRegistry",
    "CapabilityRequest",
    "CapabilityResponse",
    "create_default_kernel",
    "DuplicateCapabilityError",
    "Event",
    "EventBus",
    "HealthCheckCapability",
    "KernelError",
    "KernelMemory",
    "VeraxisKernel",
]
