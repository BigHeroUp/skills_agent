import json

import pytest

from services.knowledge_graph.governance import GovernancePolicy
from services.knowledge_graph.schema import (
    DeprecationSpec,
    DomainPackSchemaExtension,
    NodeTypeSpec,
    PropertySpec,
    RelationshipSpec,
)
from services.knowledge_graph.schema.v1 import GRAPH_SCHEMA_V1
from services.knowledge_graph.validation import QualityStatus, validate_graph


def _write(tmp_path, payload):
    path = tmp_path / "graph.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _codes(result):
    return {issue.code for issue in result.report.issues}


def test_cardinality_groups_canonical_and_legacy_relationships(tmp_path):
    payload = {
        "schema_version": 1,
        "nodes": [
            {"id": "run:1", "type": "analysis_run", "label": "Run", "properties": {}},
            {"id": "dataset:1", "type": "dataset", "label": "One", "properties": {}},
            {"id": "dataset:2", "type": "dataset", "label": "Two", "properties": {}},
        ],
        "edges": [
            {
                "source": "run:1",
                "target": "dataset:1",
                "relationship": "ANALYZED_DATASET",
                "properties": {},
            },
            {
                "source": "run:1",
                "target": "dataset:2",
                "relationship": "USES_DATASET",
                "properties": {},
            },
        ],
    }

    result = validate_graph(_write(tmp_path, payload))

    assert result.report.status == QualityStatus.INVALID
    assert "cardinality.max_per_source_exceeded" in _codes(result)
    issue = next(
        item for item in result.report.issues
        if item.code == "cardinality.max_per_source_exceeded"
    )
    assert issue.evidence["relationship"] == "ANALYZED_DATASET"
    assert issue.evidence["actual"] == 2
    assert result.report.can_write is False


def test_domain_pack_extension_is_additive_namespaced_and_read_only(tmp_path):
    extension = DomainPackSchemaExtension(
        pack_id="retail",
        version="1.0.0",
        node_types={
            "retail__campaign": NodeTypeSpec(
                "retail__campaign",
                properties=(PropertySpec("channel", required=True),),
            ),
        },
        relationships={
            "RETAIL__USES_CAMPAIGN": RelationshipSpec(
                "RETAIL__USES_CAMPAIGN",
                source_types=frozenset({"analysis_run"}),
                target_types=frozenset({"retail__campaign"}),
            ),
        },
    )
    policy = GovernancePolicy(
        policy_id="test.retail",
        version="1.0.0",
        schema=GRAPH_SCHEMA_V1,
        extensions=(extension,),
    )
    payload = {
        "schema_version": 1,
        "nodes": [
            {"id": "run:1", "type": "analysis_run", "label": "Run", "properties": {}},
            {
                "id": "retail:campaign:1",
                "type": "retail__campaign",
                "label": "Campaign",
                "properties": {"channel": "store"},
            },
        ],
        "edges": [{
            "source": "run:1",
            "target": "retail:campaign:1",
            "relationship": "RETAIL__USES_CAMPAIGN",
            "properties": {},
        }],
    }
    path = _write(tmp_path, payload)
    before = path.read_bytes()

    result = validate_graph(path, policy=policy)

    assert "schema.unknown_node_type" not in _codes(result)
    assert "schema.unknown_relationship" not in _codes(result)
    assert result.report.accepted_node_count == 2
    assert result.report.accepted_edge_count == 1
    assert path.read_bytes() == before


def test_domain_pack_extension_rejects_unscoped_names():
    with pytest.raises(ValueError, match="must start"):
        DomainPackSchemaExtension(
            pack_id="retail",
            version="1.0.0",
            node_types={"campaign": NodeTypeSpec("campaign")},
        )


def test_deprecated_extension_contracts_emit_actionable_warnings(tmp_path):
    extension = DomainPackSchemaExtension(
        pack_id="retail",
        version="1.0.0",
        node_types={
            "retail__legacy_campaign": NodeTypeSpec(
                "retail__legacy_campaign",
                properties=(PropertySpec(
                    "old_channel",
                    deprecation=DeprecationSpec(
                        since="1.0.0",
                        replacement="channel",
                        removal_version=2,
                    ),
                ),),
                deprecation=DeprecationSpec(
                    since="1.0.0",
                    replacement="retail__campaign",
                ),
            ),
        },
    )
    policy = GovernancePolicy(
        policy_id="test.retail",
        version="1.0.0",
        schema=GRAPH_SCHEMA_V1,
        extensions=(extension,),
    )
    payload = {
        "schema_version": 1,
        "nodes": [{
            "id": "retail:campaign:1",
            "type": "retail__legacy_campaign",
            "label": "Legacy",
            "properties": {"old_channel": "store"},
        }],
        "edges": [],
    }

    result = validate_graph(_write(tmp_path, payload), policy=policy)

    assert "schema.deprecated_node_type" in _codes(result)
    assert "schema.deprecated_node_property" in _codes(result)
    assert result.report.status == QualityStatus.DEGRADED
    assert result.report.severity_counts["error"] == 0
