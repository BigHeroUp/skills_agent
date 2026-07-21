import plotly.graph_objects as go
from types import SimpleNamespace

from services.knowledge_graph.graph_visualizer import (
    NODE_COLORS,
    KnowledgeGraphVisualizer,
    format_node_details_payload,
)
from services.knowledge_graph.query_engine import KnowledgeGraphQueryEngine
from services.knowledge_graph.models import KnowledgeNode


class FakeLineageQueryEngine:
    def __init__(self, column_count=2):
        self.column_count = column_count
        self.snapshot = SimpleNamespace(
            nodes=[
                KnowledgeNode("analysis_run:latest", "analysis_run", "Analisi response_time"),
                KnowledgeNode("dataset:latest", "dataset", "performance.xlsx"),
                KnowledgeNode("insight:latest:key", "insight", "key_findings"),
            ],
            edges=[],
        )

    def get_latest_analysis_runs(self, limit=1):
        return [
            {
                "id": "analysis_run:latest",
                "type": "analysis_run",
                "label": "Analisi response_time",
                "properties": {"created_at": "2026-01-01T10:00:00"},
            }
        ][:limit]

    def get_analysis_lineage(self, analysis_run_id):
        columns = [
            {
                "id": f"dataframe_column:latest:col_{index}",
                "type": "dataframe_column",
                "label": f"col_{index}",
                "properties": {"dtype": "float64"},
            }
            for index in range(self.column_count)
        ]
        return {
            "analysis_run": {
                "id": analysis_run_id,
                "type": "analysis_run",
                "label": "Analisi response_time",
                "properties": {"primary_metric": "response_time"},
            },
            "dataset": [
                {
                    "id": "dataset:latest",
                    "type": "dataset",
                    "label": "performance.xlsx",
                    "properties": {"row_count": 100},
                }
            ],
            "columns": columns,
            "insights": [
                {
                    "id": "insight:latest:key",
                    "type": "insight",
                    "label": "key_findings",
                    "properties": {"summary": "ok"},
                }
            ],
            "anomalies": [
                {
                    "id": "anomaly:a1",
                    "type": "anomaly",
                    "label": "numeric_outlier",
                    "properties": {"severity": "high"},
                }
            ],
            "root_causes": [
                {
                    "id": "root_cause:rc1",
                    "type": "root_cause",
                    "label": "Backlog operativo",
                    "properties": {"confidence_score": 0.7},
                }
            ],
            "reports": [
                {
                    "id": "report:latest",
                    "type": "report",
                    "label": "final_report",
                    "properties": {"length_chars": 500},
                }
            ],
            "domain_packs": [],
        }


def test_visualizer_returns_figure_without_json(tmp_path):
    engine = KnowledgeGraphQueryEngine(path=tmp_path / "missing.json")

    payload = KnowledgeGraphVisualizer(engine).build_latest_analysis_lineage()

    assert isinstance(payload["figure"], go.Figure)
    assert payload["nodes"] == []
    assert "non ci sono analysis_run" in payload["message"]


def test_visualizer_builds_nodes_and_edges_from_lineage():
    payload = KnowledgeGraphVisualizer(FakeLineageQueryEngine()).build_latest_analysis_lineage()

    node_types = {node["type"] for node in payload["nodes"]}
    relationships = {edge["relationship"] for edge in payload["edges"]}

    assert isinstance(payload["figure"], go.Figure)
    assert node_types >= {
        "analysis_run",
        "dataset",
        "dataframe_column",
        "insight",
        "anomaly",
        "root_cause",
        "report",
    }
    assert relationships >= {
        "ANALYZED_DATASET",
        "HAS_COLUMN",
        "PRODUCED_INSIGHT",
        "DETECTED_ANOMALY",
        "IDENTIFIED_ROOT_CAUSE",
        "GENERATED_REPORT",
    }


def test_visualizer_limits_nodes_to_eighty():
    payload = KnowledgeGraphVisualizer(FakeLineageQueryEngine(column_count=120)).build_latest_analysis_lineage()

    assert len(payload["nodes"]) == 80
    assert all(edge["source"] in {node["id"] for node in payload["nodes"]} for edge in payload["edges"])
    assert all(edge["target"] in {node["id"] for node in payload["nodes"]} for edge in payload["edges"])


def test_visualizer_uses_expected_node_colors():
    payload = KnowledgeGraphVisualizer(FakeLineageQueryEngine()).build_latest_analysis_lineage()
    node_trace = payload["figure"].data[1]
    colors = list(node_trace.marker.color)

    assert NODE_COLORS["analysis_run"] in colors
    assert NODE_COLORS["dataset"] in colors
    assert NODE_COLORS["dataframe_column"] in colors
    assert NODE_COLORS["anomaly"] in colors


def test_node_details_formatter_limits_properties():
    node = {
        "id": "dataframe_column:1",
        "type": "dataframe_column",
        "label": "response_time",
        "properties": {f"key_{index}": index for index in range(20)},
    }

    details = format_node_details_payload(node)

    assert details["label"] == "response_time"
    assert details["type"] == "dataframe_column"
    assert details["id"] == "dataframe_column:1"
    assert len(details["properties"]) == 10


def test_memory_overview_aggregates_persistent_knowledge():
    payload = KnowledgeGraphVisualizer(FakeLineageQueryEngine()).build_memory_overview()

    assert isinstance(payload["figure"], go.Figure)
    assert payload["nodes"][0]["type"] == "memory_core"
    assert any(node["type"] == "analysis_run" for node in payload["nodes"])
    assert "Memoria Veraxis attiva" in payload["message"]


def test_pipeline_memory_marks_current_and_completed_agents():
    payload = KnowledgeGraphVisualizer(FakeLineageQueryEngine()).build_pipeline_memory({
        "status": "processing",
        "current_agent": "Analyst",
        "progress": 60,
    })
    by_id = {node["id"]: node for node in payload["nodes"]}

    assert by_id["pipeline:Analyst"]["status"] == "active"
    assert by_id["pipeline:DataValidator"]["status"] == "completed"
    assert by_id["pipeline:ReportGenerator"]["status"] == "pending"
    assert "60%" in payload["message"]
