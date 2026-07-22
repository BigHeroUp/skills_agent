"""Provider for deterministic analytical Kernel capabilities."""

from core.kernel.provider import CapabilityProvider

from .analytical_count import CategoricalCountCapability


class AnalyticalCapabilityProvider(CapabilityProvider):
    name = "analytical_provider"
    version = "1.0.0"
    description = "Provides deterministic analytical capabilities"

    def list_capabilities(self) -> list[CategoricalCountCapability]:
        return [CategoricalCountCapability()]
