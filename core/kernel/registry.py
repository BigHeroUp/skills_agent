"""Capability registry for the Veraxis kernel."""

from __future__ import annotations

from .errors import DuplicateCapabilityError, KernelError


class CapabilityRegistry:
    """Deterministic in-memory registry of kernel capabilities."""

    def __init__(self) -> None:
        self._capabilities: dict[str, object] = {}

    def register(self, capability) -> None:
        name = str(getattr(capability, "name", "") or "").strip()
        if not name:
            raise KernelError("Capability name must be a non-empty string")
        if name in self._capabilities:
            raise DuplicateCapabilityError(
                f"Capability '{name}' is already registered"
            )
        self._capabilities[name] = capability

    def unregister(self, name: str) -> bool:
        return self._capabilities.pop(name, None) is not None

    def get(self, name: str):
        return self._capabilities.get(name)

    def list_capabilities(self) -> list[str]:
        return sorted(self._capabilities.keys())

    def has(self, name: str) -> bool:
        return name in self._capabilities
