from core.kernel.capability import Capability, CapabilityRequest, CapabilityResponse
from core.kernel.builtin_capabilities import HealthCheckCapability
from core.kernel.kernel import VeraxisKernel


class EchoCapability(Capability):
    name = "echo"
    version = "1.0.0"
    description = "Echo payload for deterministic tests"

    def execute(self, request: CapabilityRequest) -> CapabilityResponse:
        return CapabilityResponse(
            success=True,
            result={"payload": request.payload, "metadata": request.metadata},
        )


class BrokenCapability(Capability):
    name = "broken"
    version = "1.0.0"
    description = "Raises an error to test safe failure handling"

    def execute(self, request: CapabilityRequest) -> CapabilityResponse:
        raise RuntimeError("unexpected failure")


def test_execute_existing_capability_and_publish_lifecycle_events():
    kernel = VeraxisKernel()
    kernel.register_capability(EchoCapability())

    response = kernel.execute_capability(
        "echo",
        payload={"value": 42},
        metadata={"source": "test"},
    )

    event_types = [event.type for event in kernel.event_bus.get_events(limit=10)]

    assert response.success is True
    assert response.result["payload"] == {"value": 42}
    assert response.result["metadata"] == {"source": "test"}
    assert event_types == [
        "capability.execution.started",
        "capability.execution.completed",
    ]


def test_execute_missing_capability_returns_safe_error():
    kernel = VeraxisKernel()

    response = kernel.execute_capability("missing_capability")

    failed_events = kernel.event_bus.get_events(
        event_type="capability.execution.failed",
        limit=10,
    )

    assert response.success is False
    assert response.metadata["error_type"] == "CapabilityNotFoundError"
    assert "missing_capability" in response.errors[0]
    assert len(failed_events) == 1


def test_execute_broken_capability_returns_failure_and_failed_event():
    kernel = VeraxisKernel()
    kernel.register_capability(BrokenCapability())

    response = kernel.execute_capability("broken")

    failed_event = kernel.event_bus.get_events(
        event_type="capability.execution.failed",
        limit=1,
    )[0]

    assert response.success is False
    assert response.metadata["error_type"] == "RuntimeError"
    assert "unexpected failure" in response.errors[0]
    assert failed_event.payload["capability_name"] == "broken"


def test_kernel_memory_snapshot_is_defensive():
    kernel = VeraxisKernel()
    kernel.memory.set("analysis", {"runs": [1, 2]})

    snapshot = kernel.memory.snapshot()
    snapshot["analysis"]["runs"].append(3)

    assert kernel.memory.get("analysis") == {"runs": [1, 2]}


def test_health_check_capability_and_kernel_status():
    kernel = VeraxisKernel()
    kernel.memory.set("session_id", "run-001")
    kernel.register_capability(HealthCheckCapability(kernel))

    response = kernel.execute_capability("health_check")
    status = kernel.get_status()

    assert response.success is True
    assert response.result["status"] == "ok"
    assert "health_check" in response.result["registered_capabilities"]
    assert response.result["memory_keys_count"] == 1
    assert response.result["event_count"] >= 1
    assert status["status"] == "ok"
    assert status["capability_count"] == 1
    assert status["memory_keys_count"] == 1
