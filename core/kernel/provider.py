"""Provider contracts for grouping related kernel capabilities."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .registry import CapabilityRegistry


class CapabilityProvider(ABC):
    """Abstract provider that groups related capabilities."""

    name = ""
    version = "1.0.0"
    description = ""

    @abstractmethod
    def list_capabilities(self) -> list:
        """Return the capabilities published by this provider."""

    def register(self, registry: CapabilityRegistry) -> list[str]:
        registered_names: list[str] = []
        for capability in self.list_capabilities():
            registry.register(capability)
            registered_names.append(capability.name)
        return registered_names
