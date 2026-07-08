"""Built-in capabilities for the Veraxis kernel foundation."""

from __future__ import annotations

from .capability import Capability, CapabilityRequest, CapabilityResponse


class HealthCheckCapability(Capability):
    """Return deterministic health information about the kernel."""

    name = "health_check"
    version = "1.0.0"
    description = "Returns the current kernel runtime status"

    def __init__(self, kernel) -> None:
        self.kernel = kernel

    def execute(self, request: CapabilityRequest) -> CapabilityResponse:
        return CapabilityResponse(
            success=True,
            result={
                "status": "ok",
                "registered_capabilities": self.kernel.registry.list_capabilities(),
                "event_count": self.kernel.event_bus.event_count,
                "memory_keys_count": len(self.kernel.memory.snapshot()),
            },
            metadata={
                "capability_name": self.name,
                "request_id": request.request_id,
            },
        )
