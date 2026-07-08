from core.kernel.builtin_capabilities import HealthCheckCapability
from core.kernel.errors import DuplicateCapabilityError
from core.kernel.kernel import VeraxisKernel
from core.kernel.registry import CapabilityRegistry


def test_register_and_get_capability():
    kernel = VeraxisKernel()
    capability = HealthCheckCapability(kernel)

    kernel.register_capability(capability)

    assert kernel.registry.has("health_check") is True
    assert kernel.registry.get("health_check") is capability
    assert kernel.registry.list_capabilities() == ["health_check"]


def test_registry_prevents_duplicate_capabilities():
    kernel = VeraxisKernel()
    registry = CapabilityRegistry()
    registry.register(HealthCheckCapability(kernel))

    try:
        registry.register(HealthCheckCapability(kernel))
        assert False, "Expected DuplicateCapabilityError"
    except DuplicateCapabilityError:
        assert True
