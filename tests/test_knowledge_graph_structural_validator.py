from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from services.knowledge_graph.analysis_mapper import map_analysis_context
from services.knowledge_graph.governance import ValidationMode
from services.knowledge_graph.governance import GOVERNANCE_POLICY_V1
from services.knowledge_graph.schema import GRAPH_SCHEMA_V1
from services.knowledge_graph.store import KnowledgeGraphStore
from services.knowledge_graph.validation import QualityStatus, validate_graph
from utils.context import AgentContext


FIXTURES = Path(__file__).parent / "fixtures" / "knowledge_graph"


def _write(tmp_path, payload, name="graph.json"):
    path = tmp_path / name
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _base_graph():
    return {
        "schema_version": 1,
        "nodes": [
            {
                "id": "analysis_run:r1",
                "type": "analysis_run",
                "label": "Run",
                "properties": {
                    "created_at": "2026-01-01T00:00:00",
                    "source_type": "csv",
                    "row_count": 1,
                    "column_count": 1,
                },
            },
            {
                "id": "dataset:r1",
                "type": "dataset",
                "label": "Dataset",
                "properties": {"source_type": "csv", "row_count": 1, "column_count": 1},
            },
        ],
        "edges": [
            {
                "source": "analysis_run:r1",
                "target": "dataset:r1",
                "relationship": "ANALYZED_DATASET",
                "properties": {},
            }
        ],
    }


def _codes(result):
    return [issue.code for issue in result.report.issues]


def test_valid_v1_fixture_and_empty_graph_status():
    valid = validate_graph(FIXTURES / "v1_valid.json")

    assert valid.report.status == QualityStatus.VALID
    assert valid.report.can_consume is True
    assert valid.report.can_write is True
    assert valid.report.issues == ()


def test_empty_graph_has_explicit_status(tmp_path):
    result = validate_graph(_write(tmp_path, {"schema_version": 1, "nodes": [], "edges": []}))

    assert result.report.status == QualityStatus.EMPTY
    assert result.can_consume is True


@pytest.mark.parametrize(
    ("payload", "expected_code"),
    [
        ({"schema_version": 1, "nodes": {}, "edges": []}, "structure.nodes_not_array"),
        ({"schema_version": 1, "nodes": [], "edges": {}}, "structure.edges_not_array"),
        ({"schema_version": 1, "nodes": ["bad"], "edges": []}, "structure.node_not_object"),
        ({"schema_version": 1, "nodes": [], "edges": ["bad"]}, "structure.edge_not_object"),
        ({"schema_version": 1, "edges": []}, "structure.required_top_level_field_missing"),
        ({"schema_version": 1, "nodes": []}, "structure.required_top_level_field_missing"),
    ],
)
def test_invalid_top_level_collections_and_records_are_reported(tmp_path, payload, expected_code):
    result = validate_graph(_write(tmp_path, payload))

    assert result.report.status == QualityStatus.INVALID
    assert expected_code in _codes(result)


@pytest.mark.parametrize("payload", [[], 42, '"graph"'])
def test_top_level_non_object_is_invalid(tmp_path, payload):
    result = validate_graph(_write(tmp_path, payload))

    assert result.report.status == QualityStatus.INVALID
    assert result.can_consume is False
    assert "structure.top_level_not_object" in _codes(result)


def test_missing_empty_corrupt_and_future_version_status_precedence(tmp_path):
    missing = validate_graph(tmp_path / "missing.json")
    empty = validate_graph(_write(tmp_path, "", "empty.json"))
    corrupt = validate_graph(_write(tmp_path, "{bad", "corrupt.json"))
    future = validate_graph(_write(tmp_path, {"schema_version": 99, "nodes": ["bad"], "edges": []}, "future.json"))

    assert missing.report.status == QualityStatus.UNREADABLE
    assert empty.report.status == QualityStatus.UNREADABLE
    assert corrupt.report.status == QualityStatus.UNREADABLE
    assert future.report.status == QualityStatus.UNSUPPORTED
    assert future.accepted_nodes == ()
    assert future.quarantined_records == ()


def test_missing_and_invalid_schema_versions(tmp_path):
    missing_version = validate_graph(_write(tmp_path, {"nodes": [], "edges": []}, "missing_version.json"))
    invalid_version = validate_graph(
        _write(
            tmp_path,
            {"schema_version": "1", "nodes": [], "edges": []},
            "invalid_version.json",
        )
    )

    assert missing_version.report.graph_schema_version == 1
    assert "schema.version_missing_assumed_v1" in _codes(missing_version)
    assert missing_version.report.status == QualityStatus.EMPTY
    assert "schema.version_not_integer" in _codes(invalid_version)
    assert invalid_version.can_consume is False


def test_duplicate_json_key_and_duplicate_node_id_are_not_hidden(tmp_path):
    duplicate_key = _write(
        tmp_path,
        '{"schema_version":1,"nodes":[{"id":"dataset:1","id":"dataset:2",'
        '"type":"dataset","label":"D","properties":{}}],"edges":[]}',
        "duplicate_key.json",
    )
    graph = _base_graph()
    graph["nodes"].append(dict(graph["nodes"][1]))
    duplicate_id = validate_graph(_write(tmp_path, graph, "duplicate_id.json"))
    duplicate_key_result = validate_graph(duplicate_key)

    assert "uniqueness.duplicate_json_key" in _codes(duplicate_key_result)
    assert duplicate_key_result.quarantined_records[0].location == "/nodes/0"
    assert "uniqueness.duplicate_node_id" in _codes(duplicate_id)
    duplicate_node_quarantine = [
        item.location
        for item in duplicate_id.quarantined_records
        if "uniqueness.duplicate_node_id" in item.reason_codes
    ]
    assert duplicate_node_quarantine == ["/nodes/1", "/nodes/2"]
    assert duplicate_id.report.accepted_node_count == 1


def test_duplicate_edge_is_quarantined(tmp_path):
    graph = _base_graph()
    graph["edges"].append(dict(graph["edges"][0]))

    result = validate_graph(_write(tmp_path, graph))

    assert "uniqueness.duplicate_edge" in _codes(result)
    assert result.report.accepted_edge_count == 0
    assert [item.location for item in result.quarantined_records] == ["/edges/0", "/edges/1"]
    assert [item.raw_index for item in result.quarantined_records] == [0, 1]


@pytest.mark.parametrize(
    ("field", "value", "expected_code"),
    [
        ("source", "analysis_run:missing", "referential.dangling_source"),
        ("target", "dataset:missing", "referential.dangling_target"),
    ],
)
def test_dangling_endpoints_are_rejected(tmp_path, field, value, expected_code):
    graph = _base_graph()
    graph["edges"][0][field] = value

    result = validate_graph(_write(tmp_path, graph))

    assert expected_code in _codes(result)
    assert result.report.accepted_edge_count == 0


def test_endpoint_type_mismatch_and_self_loop_are_rejected(tmp_path):
    mismatch = _base_graph()
    mismatch["edges"][0]["source"] = "dataset:r1"
    mismatch_result = validate_graph(_write(tmp_path, mismatch, "mismatch.json"))

    self_loop = _base_graph()
    self_loop["edges"][0] = {
        "source": "analysis_run:r1",
        "target": "analysis_run:r1",
        "relationship": "UNKNOWN_RELATION",
        "properties": {},
    }
    self_loop_result = validate_graph(_write(tmp_path, self_loop, "self_loop.json"))

    assert "referential.endpoint_type_mismatch" in _codes(mismatch_result)
    assert "referential.self_loop_not_allowed" in _codes(self_loop_result)


def test_naming_violations_are_warnings_for_legacy_compatibility(tmp_path):
    graph = _base_graph()
    graph["nodes"][1]["type"] = "DatasetType"
    graph["nodes"][1]["properties"]["Bad-Key"] = 1
    graph["edges"][0]["relationship"] = "bad relation"

    result = validate_graph(_write(tmp_path, graph))

    assert "naming.node_type_not_lower_snake_case" in _codes(result)
    assert "naming.property_key_not_lower_snake_case" in _codes(result)
    assert "naming.relationship_not_upper_snake_case" in _codes(result)
    assert all(
        issue.severity.value == "warning"
        for issue in result.report.issues
        if issue.category in {"naming", "schema_compatibility"}
    )


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_values_are_errors_and_quarantine_the_record(tmp_path, constant):
    raw = (
        '{"schema_version":1,"nodes":[{"id":"analysis_run:r1","type":"analysis_run",'
        '"label":"Run","properties":{"confidence_score":'
        + constant
        + '}}],"edges":[]}'
    )

    result = validate_graph(_write(tmp_path, raw))

    assert "structure.non_finite_number" in _codes(result)
    assert result.report.accepted_node_count == 0
    assert result.quarantined_records[0].reason_codes == ("structure.non_finite_number",)
    json.dumps(result.report.to_dict(), allow_nan=False)


def test_legacy_alias_unknown_types_and_unknown_relationships_are_warnings(tmp_path):
    legacy = validate_graph(FIXTURES / "v1_legacy.json")
    unknown = _base_graph()
    unknown["nodes"].append({
        "id": "custom:1",
        "type": "custom_node",
        "label": "Custom",
        "properties": {},
    })
    unknown["edges"].append({
        "source": "analysis_run:r1",
        "target": "custom:1",
        "relationship": "CUSTOM_LINK",
        "properties": {},
    })
    unknown_result = validate_graph(_write(tmp_path, unknown))

    assert "schema.legacy_relationship_alias" in _codes(legacy)
    assert legacy.report.status == QualityStatus.DEGRADED
    assert "schema.unknown_node_type" in _codes(unknown_result)
    assert "schema.unknown_relationship" in _codes(unknown_result)
    assert unknown_result.report.accepted_edge_count == 2


def test_required_and_recommended_properties_and_partial_records(tmp_path):
    graph = {
        "schema_version": 1,
        "nodes": [
            {"id": "python_file:a.py", "type": "python_file", "label": "a.py", "properties": {}},
            {"id": "dataset:1", "type": "dataset", "label": "D", "properties": {}},
            {"type": "dataset", "label": "Missing id", "properties": {}},
        ],
        "edges": [],
    }

    result = validate_graph(_write(tmp_path, graph))

    assert "property.required_node_property_missing" in _codes(result)
    assert "property.recommended_node_property_missing" in _codes(result)
    assert "identity.node_id_missing_or_empty" in _codes(result)
    assert result.report.accepted_node_count == 1
    assert result.report.quarantined_record_count == 2


def test_missing_edge_fields_and_empty_node_label_are_reported(tmp_path):
    graph = _base_graph()
    graph["nodes"][1]["label"] = ""
    graph["edges"].append({"source": "analysis_run:r1", "properties": {}})

    result = validate_graph(_write(tmp_path, graph))

    assert "property.node_label_missing_or_empty" in _codes(result)
    assert "structure.edge_target_missing_or_empty" in _codes(result)
    assert "structure.edge_relationship_missing_or_empty" in _codes(result)
    assert any(item.location == "/edges/1" for item in result.quarantined_records)


def test_isolated_nodes_are_classified_by_type(tmp_path):
    graph = {
        "schema_version": 1,
        "nodes": [
            {"id": "python_file:a.py", "type": "python_file", "label": "a.py", "properties": {"path": "a.py"}},
            {
                "id": "analysis_run:r1",
                "type": "analysis_run",
                "label": "Run",
                "properties": {"created_at": "x", "source_type": "csv", "row_count": 0, "column_count": 0},
            },
        ],
        "edges": [],
    }

    result = validate_graph(_write(tmp_path, graph))
    orphan_issues = [issue for issue in result.report.issues if issue.code == "coverage.isolated_node"]

    assert [issue.severity.value for issue in orphan_issues] == ["warning", "info"]


def test_issue_order_report_determinism_and_strict_permissive_admissibility(tmp_path):
    graph = _base_graph()
    graph["nodes"].append({"id": "", "type": "dataset", "label": "Bad", "properties": {}})
    path = _write(tmp_path, graph)

    permissive_a = validate_graph(path, mode=ValidationMode.PERMISSIVE)
    permissive_b = validate_graph(path, mode=ValidationMode.PERMISSIVE)
    strict = validate_graph(path, mode=ValidationMode.STRICT)

    assert permissive_a.to_dict() == permissive_b.to_dict()
    assert [issue.to_dict() for issue in permissive_a.report.issues] == [
        issue.to_dict() for issue in strict.report.issues
    ]
    assert permissive_a.can_consume is True
    assert strict.can_consume is False
    assert permissive_a.can_write is False
    assert strict.can_write is False
    assert json.dumps(permissive_a.report.to_dict(), allow_nan=False)
    permissive_report = permissive_a.report.to_dict()
    strict_report = strict.report.to_dict()
    permissive_report.pop("can_consume")
    permissive_report.pop("can_write")
    strict_report.pop("can_consume")
    strict_report.pop("can_write")
    assert permissive_report == strict_report
    assert permissive_a.accepted_nodes == strict.accepted_nodes
    assert permissive_a.accepted_edges == strict.accepted_edges
    assert permissive_a.quarantined_records == strict.quarantined_records
    dimensions = {item.name: item.status.value for item in permissive_a.report.dimensions}
    assert dimensions["identity"] == "fail"
    assert set(dimensions) == {
        "document_structure",
        "identity",
        "naming",
        "uniqueness",
        "referential_integrity",
        "schema_compatibility",
        "property_completeness",
        "graph_coverage",
    }


def test_report_does_not_expose_absolute_path_or_raw_dataframe_rows(tmp_path):
    secret_row = "RAW_CUSTOMER_ROW_SHOULD_NOT_APPEAR"
    secret_label = "SENSITIVE_LABEL_SHOULD_NOT_APPEAR"
    graph = _base_graph()
    graph["nodes"].append({
        "id": "dataset:private",
        "type": "dataset",
        "label": secret_label,
        "properties": {"raw_rows": [secret_row]},
    })
    path = _write(tmp_path, graph)

    result = validate_graph(path)
    serialized_report = json.dumps(result.report.to_dict(), allow_nan=False)
    serialized_result = json.dumps(result.to_dict(), allow_nan=False)

    assert str(tmp_path) not in serialized_report
    assert str(tmp_path) not in serialized_result
    assert secret_row not in serialized_report
    assert secret_row not in serialized_result
    assert secret_label not in serialized_report
    assert secret_label not in serialized_result


def test_models_are_deeply_immutable_and_remain_json_serializable(tmp_path):
    result = validate_graph(FIXTURES / "v1_valid.json")
    report_with_nested_coverage = replace(
        result.report,
        coverage={"nested": {"items": [1, 2]}},
    )

    with pytest.raises(TypeError):
        result.accepted_nodes[0]["properties"]["row_count"] = 2
    with pytest.raises(TypeError):
        report_with_nested_coverage.coverage["nested"]["changed"] = True
    with pytest.raises(TypeError):
        GRAPH_SCHEMA_V1.node_types["new"] = object()
    with pytest.raises(TypeError):
        GOVERNANCE_POLICY_V1.issue_severity_overrides["x"] = object()

    missing_version_path = _write(tmp_path, {"nodes": [], "edges": []})
    missing_version_result = validate_graph(missing_version_path)
    with pytest.raises(TypeError):
        missing_version_result.report.issues[0].evidence["changed"] = True

    assert json.dumps(report_with_nested_coverage.to_dict(), allow_nan=False)


def test_top_level_duplicate_key_is_blocking_without_arbitrary_record_quarantine(tmp_path):
    raw = '{"schema_version":1,"nodes":[],"nodes":[],"edges":[]}'

    result = validate_graph(_write(tmp_path, raw))

    assert result.report.status == QualityStatus.INVALID
    assert result.can_consume is False
    assert result.quarantined_records == ()


def test_nested_duplicate_outside_graph_records_is_reported_without_quarantine(tmp_path):
    raw = (
        '{"schema_version":1,"metadata":{"key":1,"key":2},'
        '"nodes":[],"edges":[]}'
    )

    result = validate_graph(_write(tmp_path, raw))

    assert "uniqueness.duplicate_json_key" in _codes(result)
    assert result.quarantined_records == ()


@pytest.mark.parametrize(
    ("raw", "expected_kind", "expected_location"),
    [
        (
            '{"schema_version":1,"nodes":[{"id":"custom:1","type":"custom_node",'
            '"label":"Custom","properties":{"nested":{"key":1,"key":2}}}],"edges":[]}',
            "node",
            "/nodes/0",
        ),
        (
            '{"schema_version":1,"nodes":[{"id":"custom:1","type":"custom_node",'
            '"label":"Custom","properties":{}}],"edges":[{"source":"custom:1",'
            '"target":"custom:1","relationship":"CUSTOM_LINK",'
            '"properties":{"key":1,"key":2}}]}',
            "edge",
            "/edges/0",
        ),
    ],
)
def test_nested_duplicate_key_quarantines_only_its_identifiable_record(
    tmp_path,
    raw,
    expected_kind,
    expected_location,
):
    result = validate_graph(_write(tmp_path, raw))

    duplicate_quarantine = [
        item
        for item in result.quarantined_records
        if "uniqueness.duplicate_json_key" in item.reason_codes
    ]
    assert len(duplicate_quarantine) == 1
    assert duplicate_quarantine[0].kind == expected_kind
    assert duplicate_quarantine[0].location == expected_location


def test_current_analysis_mapper_and_store_emit_validator_compatible_v1(tmp_path):
    context = AgentContext(
        user_input="Analizza response_time",
        raw_data={
            "dataframe": pd.DataFrame({
                "created_at": pd.to_datetime(["2026-01-01", "2026-01-02"]),
                "response_time": [10.0, 20.0],
            })
        },
        metadata={"source_type": "csv", "filename": "metrics.csv"},
        created_at=datetime(2026, 1, 3, 10, 0, 0),
    )
    context.primary_metric = "response_time"
    context.time_axis = "created_at"
    context.insights = {"summary": "Trend stabile"}
    context.anomaly_detection_results = {
        "anomalies": [{
            "anomaly_id": "a1",
            "anomaly_type": "numeric_outlier",
            "severity": "low",
            "affected_column": "response_time",
        }]
    }
    context.root_cause_results = {
        "possible_causes": [{
            "cause_id": "rc1",
            "title": "Variazione limitata",
            "affected_metrics": ["response_time"],
            "related_anomalies": ["a1"],
        }]
    }
    context.final_report = "# Report"
    context.domain_pack_context = {"status": "detected", "pack_id": "operations"}

    path = tmp_path / "mapper_graph.json"
    KnowledgeGraphStore(path).save(map_analysis_context(context))
    result = validate_graph(path)

    assert result.report.status == QualityStatus.DEGRADED
    assert result.report.severity_counts["error"] == 0
    assert result.report.accepted_node_count > 0
    assert result.report.accepted_edge_count > 0
    assert "schema.legacy_relationship_alias" in _codes(result)
