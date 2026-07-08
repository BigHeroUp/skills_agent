"""Bootstrap helpers for the experimental Veraxis kernel runtime."""

from __future__ import annotations

from pathlib import Path

from core.capabilities import KnowledgeGraphQueryCapability

from .builtin_capabilities import HealthCheckCapability
from .kernel import VeraxisKernel


def create_default_kernel(path: str | Path | None = None) -> VeraxisKernel:
    """Create the default experimental kernel with built-in capabilities."""

    kernel = VeraxisKernel()
    kernel.register_capability(HealthCheckCapability(kernel))
    kernel.register_capability(KnowledgeGraphQueryCapability(path=path))
    return kernel
