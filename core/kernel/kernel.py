"""Kernel runtime foundation for Veraxis."""

from __future__ import annotations

from typing import Any

from .capability import CapabilityRequest, CapabilityResponse
from .errors import CapabilityExecutionError, CapabilityNotFoundError
from .events import Event, EventBus
from .memory import KernelMemory
from .registry import CapabilityRegistry


class VeraxisKernel:
    """Parallel, non-invasive kernel runtime foundation."""

    def __init__(
        self,
        registry: CapabilityRegistry | None = None,
        event_bus: EventBus | None = None,
        memory: KernelMemory | None = None,
    ) -> None:
        self.registry = registry or CapabilityRegistry()
        self.event_bus = event_bus or EventBus()
        self.memory = memory or KernelMemory()

    def register_capability(self, capability) -> None:
        self.registry.register(capability)

    def execute_capability(
        self,
        name: str,
        payload: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CapabilityResponse:
        request = CapabilityRequest(
            capability_name=name,
            payload=dict(payload or {}),
            metadata=dict(metadata or {}),
        )
        self.publish_event(
            "capability.execution.started",
            payload={"capability_name": name, "request_id": request.request_id},
            metadata=request.metadata,
        )

        capability = self.registry.get(name)
        if capability is None:
            error = CapabilityNotFoundError(f"Capability '{name}' is not registered")
            self.publish_event(
                "capability.execution.failed",
                payload={
                    "capability_name": name,
                    "request_id": request.request_id,
                    "error": str(error),
                },
                metadata=request.metadata,
            )
            return CapabilityResponse(
                success=False,
                errors=[str(error)],
                metadata={
                    "capability_name": name,
                    "request_id": request.request_id,
                    "error_type": error.__class__.__name__,
                },
            )

        try:
            response = capability.execute(request)
            response.metadata = {
                **dict(response.metadata or {}),
                "capability_name": name,
                "request_id": request.request_id,
            }
            if response.success:
                self.publish_event(
                    "capability.execution.completed",
                    payload={
                        "capability_name": name,
                        "request_id": request.request_id,
                        "success": response.success,
                    },
                    metadata=response.metadata,
                )
            else:
                self.publish_event(
                    "capability.execution.failed",
                    payload={
                        "capability_name": name,
                        "request_id": request.request_id,
                        "error": "; ".join(response.errors) if response.errors else "Capability execution failed",
                    },
                    metadata=response.metadata,
                )
            return response
        except Exception as exc:
            error = CapabilityExecutionError(
                f"Capability '{name}' failed: {exc}"
            )
            self.publish_event(
                "capability.execution.failed",
                payload={
                    "capability_name": name,
                    "request_id": request.request_id,
                    "error": str(error),
                },
                metadata=request.metadata,
            )
            return CapabilityResponse(
                success=False,
                errors=[str(error)],
                metadata={
                    "capability_name": name,
                    "request_id": request.request_id,
                    "error_type": exc.__class__.__name__,
                },
            )

    def publish_event(
        self,
        type: str,
        payload: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Event:
        event = Event(
            type=type,
            payload=dict(payload or {}),
            metadata=dict(metadata or {}),
        )
        return self.event_bus.publish(event)

    def get_status(self) -> dict[str, Any]:
        registered_capabilities = self.registry.list_capabilities()
        return {
            "status": "ok",
            "registered_capabilities": registered_capabilities,
            "capability_count": len(registered_capabilities),
            "event_count": self.event_bus.event_count,
            "memory_keys_count": len(self.memory.snapshot()),
        }
