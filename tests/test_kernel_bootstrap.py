from core.kernel.bootstrap import create_default_kernel


def test_default_kernel_registers_expected_capabilities():
    kernel = create_default_kernel()

    assert kernel.registry.has("health_check") is True
    assert kernel.registry.has("knowledge_graph.query") is True
    assert kernel.registry.has("experience.query") is True
    assert kernel.registry.list_capabilities() == [
        "experience.query",
        "health_check",
        "knowledge_graph.query",
    ]
