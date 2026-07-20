import json

import pytest

from services.knowledge_graph.consumption import (
    ConsumerGovernanceMode,
    GovernedGraphReader,
    GraphConsumptionBlocked,
)
from services.knowledge_graph.query_engine import KnowledgeGraphQueryEngine
from services.knowledge_graph.store import KnowledgeGraphStore
from services.knowledge_graph.validation import QualityStatus


def _write(tmp_path, payload):
    path = tmp_path / "graph.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _valid_graph():
    return {
        "schema_version": 1,
        "nodes": [{
            "id": "file:one",
            "type": "python_file",
            "label": "one.py",
            "properties": {"path": "one.py"},
        }],
        "edges": [],
    }


def test_legacy_remains_the_default_and_does_not_validate(tmp_path):
    path = _write(tmp_path, _valid_graph())

    engine = KnowledgeGraphQueryEngine(path=path)

    assert engine.governance_mode == ConsumerGovernanceMode.LEGACY
    assert engine.validation_result is None
    assert len(engine.snapshot.nodes) == 1


def test_observe_preserves_legacy_snapshot_and_exposes_report(tmp_path):
    payload = _valid_graph()
    payload["nodes"].append(dict(payload["nodes"][0]))
    path = _write(tmp_path, payload)
    before = path.read_bytes()

    engine = KnowledgeGraphQueryEngine(
        path=path,
        governance_mode=ConsumerGovernanceMode.OBSERVE,
    )

    assert len(engine.snapshot.nodes) == 1
    assert engine.validation_result.report.status == QualityStatus.INVALID
    assert engine.validation_result.can_consume is False
    assert path.read_bytes() == before


def test_enforce_blocks_invalid_graph_before_legacy_normalization(tmp_path):
    payload = _valid_graph()
    payload["nodes"].append(dict(payload["nodes"][0]))
    store = KnowledgeGraphStore(_write(tmp_path, payload))

    with pytest.raises(GraphConsumptionBlocked) as exc_info:
        GovernedGraphReader(store).load(ConsumerGovernanceMode.ENFORCE)

    assert exc_info.value.result.report.status == QualityStatus.INVALID
    assert exc_info.value.result.report.accepted_node_count == 0


def test_enforce_builds_snapshot_only_from_accepted_records(tmp_path):
    path = _write(tmp_path, _valid_graph())
    before = path.read_bytes()

    load = GovernedGraphReader(KnowledgeGraphStore(path)).load("enforce")

    assert load.is_governed is True
    assert load.validation.can_consume is True
    assert [node.id for node in load.snapshot.nodes] == ["file:one"]
    assert path.read_bytes() == before


def test_enforce_blocks_missing_graph_while_legacy_returns_empty(tmp_path):
    store = KnowledgeGraphStore(tmp_path / "missing.json")

    assert GovernedGraphReader(store).load("legacy").snapshot.nodes == []
    with pytest.raises(GraphConsumptionBlocked):
        GovernedGraphReader(store).load("enforce")
