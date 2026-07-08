"""Bootstrap helpers for the experimental Veraxis kernel runtime."""

from __future__ import annotations

from pathlib import Path

from .builtin_capabilities import HealthCheckCapability
from .kernel import VeraxisKernel


def create_default_kernel(
    path: str | Path | None = None,
    experience_path: str | Path | None = None,
) -> VeraxisKernel:
    """Create the default experimental kernel with built-in capabilities."""

    from core.capabilities import (
        ExperienceCapabilityProvider,
        KnowledgeGraphCapabilityProvider,
    )

    kernel = VeraxisKernel()
    kernel.register_capability(HealthCheckCapability(kernel))
    KnowledgeGraphCapabilityProvider(path=path).register(kernel.registry)
    ExperienceCapabilityProvider(
        kg_path=path,
        experience_path=experience_path,
    ).register(kernel.registry)
    return kernel
