from __future__ import annotations

from services.knowledge_graph.models import KnowledgeEdge, KnowledgeNode
from services.knowledge_graph.store import KnowledgeGraphStore

from core.capabilities import KnowledgeGraphQueryCapability
from core.kernel.bootstrap import create_default_kernel
from core.kernel.capability import CapabilityRequest
from scripts.kernel_query_knowledge_graph import main


def _build_store(path):
    store = KnowledgeGraphStore(path)
    nodes = [
        KnowledgeNode(
            id="python_file:utils/chart_generator.py",
            type="python_file",
            label="utils/chart_generator.py",
            properties={"path": "utils/chart_generator.py"},
        ),
        KnowledgeNode(
            id="python_function:utils/chart_generator.py:ChartGenerator.generate_dashboard_charts",
            type="python_function",
            label="generate_dashboard_charts",
            properties={
                "file": "utils/chart_generator.py",
                "qualname": "ChartGenerator.generate_dashboard_charts",
            },
        ),
    ]
    edges = [
        KnowledgeEdge(
            "python_file:utils/chart_generator.py",
            "python_function:utils/chart_generator.py:ChartGenerator.generate_dashboard_charts",
            "CONTAINS",
        ),
    ]
    for node in nodes:
        store.upsert_node(node)
    for edge in edges:
        store.upsert_edge(edge)
    store.save()
    return store


def test_capability_answers_valid_question(tmp_path):
    path = tmp_path / "kg.json"
    _build_store(path)
    capability = KnowledgeGraphQueryCapability(path=path)

    response = capability.execute(
        CapabilityRequest(
            capability_name="knowledge_graph.query",
            payload={
                "question": "quali funzioni generano grafici?",
                "mode": "deterministic",
            },
        )
    )

    assert response.success is True
    assert response.result["execution_type"] == "deterministic_kg_query"
    assert response.result["confidence"] > 0.5
    assert response.result["matches"][0]["type"] == "python_function"


def test_capability_fails_without_question():
    capability = KnowledgeGraphQueryCapability(path="missing.json")

    response = capability.execute(
        CapabilityRequest(
            capability_name="knowledge_graph.query",
            payload={"mode": "deterministic"},
        )
    )

    assert response.success is False
    assert response.metadata["error_type"] == "ValidationError"
    assert "question" in response.errors[0]


def test_capability_fails_with_non_deterministic_mode():
    capability = KnowledgeGraphQueryCapability(path="missing.json")

    response = capability.execute(
        CapabilityRequest(
            capability_name="knowledge_graph.query",
            payload={
                "question": "quali funzioni generano grafici?",
                "mode": "llm",
            },
        )
    )

    assert response.success is False
    assert "deterministic" in response.errors[0]


def test_kernel_execution_publishes_started_and_completed_events(tmp_path):
    path = tmp_path / "kg.json"
    _build_store(path)
    kernel = create_default_kernel(path=path)

    response = kernel.execute_capability(
        "knowledge_graph.query",
        payload={
            "question": "quali funzioni generano grafici?",
            "mode": "deterministic",
        },
    )
    event_types = [event.type for event in kernel.event_bus.get_events(limit=10)]

    assert response.success is True
    assert event_types == [
        "capability.execution.started",
        "capability.execution.completed",
    ]


def test_kernel_execution_failure_publishes_failed_event(tmp_path):
    path = tmp_path / "kg.json"
    _build_store(path)
    kernel = create_default_kernel(path=path)

    response = kernel.execute_capability(
        "knowledge_graph.query",
        payload={"mode": "deterministic"},
    )
    event_types = [event.type for event in kernel.event_bus.get_events(limit=10)]

    assert response.success is False
    assert event_types == [
        "capability.execution.started",
        "capability.execution.failed",
    ]


def test_capability_handles_missing_graph_without_crashing(tmp_path):
    capability = KnowledgeGraphQueryCapability(path=tmp_path / "missing.json")

    response = capability.execute(
        CapabilityRequest(
            capability_name="knowledge_graph.query",
            payload={
                "question": "quali file?",
                "mode": "deterministic",
            },
        )
    )

    assert response.success is True
    assert "Knowledge Graph non trovato" in response.result["answer"]


def test_capability_observe_mode_exposes_quality_status(tmp_path):
    path = tmp_path / "kg.json"
    _build_store(path)
    capability = KnowledgeGraphQueryCapability(path=path)

    response = capability.execute(CapabilityRequest(
        capability_name="knowledge_graph.query",
        payload={
            "question": "quali funzioni generano grafici?",
            "mode": "deterministic",
            "governance": "observe",
        },
    ))

    assert response.success is True
    assert response.metadata["governance"] == "observe"
    assert response.metadata["quality_status"] == "invalid"


def test_capability_enforce_mode_blocks_missing_graph(tmp_path):
    capability = KnowledgeGraphQueryCapability(path=tmp_path / "missing.json")

    response = capability.execute(CapabilityRequest(
        capability_name="knowledge_graph.query",
        payload={
            "question": "quali file?",
            "mode": "deterministic",
            "governance": "enforce",
        },
    ))

    assert response.success is False
    assert response.metadata["error_type"] == "GraphConsumptionBlocked"
    assert response.metadata["quality_status"] == "unreadable"


def test_cli_main_is_testable_without_subprocess(tmp_path, monkeypatch, capsys):
    path = tmp_path / "kg.json"
    _build_store(path)

    from scripts import kernel_query_knowledge_graph as cli_module

    original_default_path = cli_module.KnowledgeGraphStore.DEFAULT_PATH
    monkeypatch.setattr(
        cli_module.KnowledgeGraphStore,
        "DEFAULT_PATH",
        path,
    )

    try:
        exit_code = main(["quali", "funzioni", "generano", "grafici?"])
    finally:
        monkeypatch.setattr(
            cli_module.KnowledgeGraphStore,
            "DEFAULT_PATH",
            original_default_path,
        )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "deterministic_kg_query" in captured.out
    assert "generate_dashboard_charts" in captured.out
