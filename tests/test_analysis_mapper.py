import pandas as pd

from services.knowledge_graph.analysis_mapper import map_analysis_context
from utils.context import AgentContext


def test_analysis_mapper_creates_metadata_only_graph_snapshot():
    context = AgentContext(
        user_input="Analizza SLA e anomalie",
        raw_data={
            "dataframe": pd.DataFrame({
                "cliente": ["A", "B"],
                "duration": [12, 42],
            })
        },
        metadata={
            "source_type": "csv",
            "filename": "tickets.csv",
            "password": "do-not-store",
        },
    )
    context.insights = {"key_findings": ["Duration alta su un record"], "processed_data": {"raw": "skip"}}
    context.anomaly_detection_results = {
        "status": "computed",
        "anomalies": [
            {
                "anomaly_id": "a1",
                "anomaly_type": "sla_violation",
                "severity": "high",
                "confidence_score": 0.82,
                "affected_column": "duration",
                "observed_value": 42,
            }
        ],
    }
    context.root_cause_results = {
        "status": "computed",
        "possible_causes": [
            {
                "cause_id": "rc1",
                "title": "Possibile backlog operativo",
                "severity": "high",
                "confidence_score": 0.7,
                "affected_metrics": ["duration"],
                "related_anomalies": ["a1"],
            }
        ],
    }
    context.final_report = "# Report\nRisultato sintetico"
    context.domain_pack_context = {"status": "detected", "pack_id": "telepedaggio"}

    snapshot = map_analysis_context(context)
    nodes_by_type = {}
    for node in snapshot.nodes:
        nodes_by_type.setdefault(node.type, []).append(node)
    relationships = {edge.relationship for edge in snapshot.edges}

    assert len(nodes_by_type["analysis_run"]) == 1
    assert len(nodes_by_type["dataset"]) == 1
    assert {node.label for node in nodes_by_type["dataframe_column"]} == {"cliente", "duration"}
    assert nodes_by_type["dataset"][0].properties["row_count"] == 2
    assert nodes_by_type["dataset"][0].properties["column_count"] == 2
    assert "password" not in nodes_by_type["analysis_run"][0].properties
    assert nodes_by_type["anomaly"][0].properties["affected_column"] == "duration"
    assert "observed_value" not in nodes_by_type["anomaly"][0].properties
    assert nodes_by_type["root_cause"][0].label == "Possibile backlog operativo"
    assert nodes_by_type["report"][0].properties["length_chars"] == len(context.final_report)
    assert nodes_by_type["domain_pack"][0].label == "telepedaggio"
    assert "USES_DATASET" in relationships
    assert "HAS_COLUMN" in relationships
    assert "DETECTED_ANOMALY" in relationships
    assert "PROPOSED_ROOT_CAUSE" in relationships
    assert "GENERATED_REPORT" in relationships
