import json
from pathlib import Path

import pytest

from services.production.health import build_runtime_health
from services.production.limits import ProductFlowLimits
from services.production.observability import ProductFlowTelemetry, ProductFlowTimeout
from services.production.runtime_guard import ProductFlowBusy, product_flow_guard
from services.production.store_safety import atomic_write_json
from scripts import production_health


def test_atomic_write_preserves_previous_file_when_limit_is_exceeded(tmp_path):
    path = tmp_path / "state.json"
    atomic_write_json(path, {"version": 1}, max_bytes=100)
    previous = path.read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="exceeds configured limit"):
        atomic_write_json(path, {"payload": "x" * 200}, max_bytes=50)

    assert path.read_text(encoding="utf-8") == previous
    assert json.loads(previous) == {"version": 1}


def test_runtime_guard_rejects_overlapping_execution(tmp_path):
    resource = tmp_path / "graph.json"
    with product_flow_guard(resource, timeout_seconds=0):
        with pytest.raises(ProductFlowBusy):
            with product_flow_guard(resource, timeout_seconds=0):
                pass


def test_telemetry_records_success_and_soft_deadline():
    ticks = iter((0.0, 0.1, 0.1, 1.0, 3.1, 3.1))
    telemetry = ProductFlowTelemetry("run-1", stage_timeout_seconds=1, clock=lambda: next(ticks))

    assert telemetry.run("fast", lambda: 42) == 42
    with pytest.raises(ProductFlowTimeout):
        telemetry.run("slow", lambda: None)

    assert [item.status for item in telemetry.metrics] == ["completed", "timeout"]


def test_limits_read_environment(monkeypatch):
    monkeypatch.setenv("PRODUCT_FLOW_MAX_CANDIDATES", "7")
    monkeypatch.setenv("PRODUCT_FLOW_STAGE_TIMEOUT_SECONDS", "9")

    limits = ProductFlowLimits.from_environment()

    assert limits.max_candidates == 7
    assert limits.stage_timeout_seconds == 9


def test_health_reports_missing_required_graph(tmp_path):
    report = build_runtime_health(
        kg_path=tmp_path / "missing.json",
        experience_path=tmp_path / "optional.json",
    )

    assert report["status"] == "unhealthy"
    assert report["resources"]["knowledge_graph"]["status"] == "missing"
    assert report["resources"]["experience_store"]["status"] == "not_initialized"


def test_health_reports_ready_resources(tmp_path):
    graph = tmp_path / "graph.json"
    experience = tmp_path / "experience.json"
    graph.write_text("{}", encoding="utf-8")
    experience.write_text("{}", encoding="utf-8")

    report = build_runtime_health(kg_path=graph, experience_path=experience)

    assert report["status"] == "healthy"


def test_health_cli_returns_success_for_ready_resources(tmp_path, capsys):
    graph = tmp_path / "graph.json"
    experience = tmp_path / "experience.json"
    graph.write_text("{}", encoding="utf-8")
    experience.write_text("{}", encoding="utf-8")

    exit_code = production_health.main([
        "--knowledge-graph", str(graph),
        "--experience-store", str(experience),
    ])

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out)["status"] == "healthy"
