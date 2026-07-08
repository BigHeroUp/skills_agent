"""Provider for experience-related kernel capabilities."""

from __future__ import annotations

from pathlib import Path

from core.kernel.provider import CapabilityProvider

from .experience_query import ExperienceQueryCapability


class ExperienceCapabilityProvider(CapabilityProvider):
    """Register analytical experience capabilities."""

    name = "experience_provider"
    version = "1.0.0"
    description = "Provides deterministic analytical experience capabilities"

    def __init__(
        self,
        kg_path: str | Path | None = None,
        experience_path: str | Path | None = None,
    ) -> None:
        self.kg_path = kg_path
        self.experience_path = experience_path

    def list_capabilities(self) -> list[ExperienceQueryCapability]:
        return [
            ExperienceQueryCapability(
                kg_path=self.kg_path,
                experience_path=self.experience_path,
            )
        ]
