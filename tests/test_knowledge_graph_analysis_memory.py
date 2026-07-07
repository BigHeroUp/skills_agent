import pandas as pd

from services.knowledge_graph.analysis_mapper import map_analysis_context
from services.knowledge_graph.models import KnowledgeEdge, KnowledgeNode
from services.knowledge_graph.query_engine import KnowledgeGraphQueryEngine
from services.knowledge_graph.store import KnowledgeGraphStore
from utils.context import AgentContext


def _context(user_input="Analizza response_time", created_at=None):
    context = AgentContext(
        user_input=user_input,
        raw_data={
            "dataframe": pd.DataFrame({
                "created_at": pd.to_datetime(["2026-01-01", "2026-01-02", None]),
                "response_time": [120.0, None, 350.0],
                "status": ["ok", "ko", "ok"],
            })
        },
        metadata={"source_type": "excel", "filename": "performance.xlsx"},
    )
    if created_at is not None:
        context.created_at = created_at
    context.primary_metric = "response_time"
    context.time_axis = "created_at"
    context.confidence_score = 0.77
    context.plan_source = "new"
    context.autonomous_mode = True
    context.semantic_columns = {
        "created_at": {"semantic_role": "time_axis"},
        "response_time": {"semantic_role": "performance_metric"},
    }
    context.insights = {"key_findings": ["Response time alto su alcuni record"]}
    context.anomaly_detection_results = {
        "anomalies": [
            {
                "anomaly_id": "a-response-time",
                "anomaly_type": "numeric_outlier",
                "severity": "high",
                "confidence_score": 0.82,
                "affected_column": "response_time",
            }
        ]
    }
    context.root_cause_results = {
        "possible_causes": [
            {
                "cause_id": "rc-backlog",
                "title": "Possibile backlog operativo",
                "severity": "high",
                "confidence_score": 0.71,
                "affected_metrics": ["response_time"],
                "related_anomalies": ["a-response-time"],
            }
        ]
    }
    context.final_report = "# Report\nAnalisi response_time."
    context.domain_pack_context = {"status": "detected", "pack_id": "operations"}
    return context


def _save_snapshot(path, snapshot):
    store = KnowledgeGraphStore(path)
    for node in snapshot.nodes:
        store.upsert_node(node)
    for edge in snapshot.edges:
        store.upsert_edge(edge)
    store.save()
    return store


def test_mapper_creates_explicit_analysis_memory_relationships():
    snapshot = map_analysis_context(_context())
    relationships = {edge.relationship for edge in snapshot.edges}
    nodes_by_type = {}
    for node in snapshot.nodes:
        nodes_by_type.setdefault(node.type, []).append(node)

    assert "ANALYZED_DATASET" in relationships
    assert "HAS_COLUMN" in relationships
    assert "PRODUCED_INSIGHT" in relationships
    assert "DETECTED_ANOMALY" in relationships
    assert "IDENTIFIED_ROOT_CAUSE" in relationships
    assert "GENERATED_REPORT" in relationships
    assert "USED_DOMAIN_PACK" in relationships

    run = nodes_by_type["analysis_run"][0]
    assert run.properties["row_count"] == 3
    assert run.properties["column_count"] == 3
    assert run.properties["primary_metric"] == "response_time"
    assert run.properties["time_axis"] == "created_at"
    assert run.properties["confidence_score"] == 0.77
    assert run.properties["autonomous_mode"] is True

    columns = {node.label: node.properties for node in nodes_by_type["dataframe_column"]}
    assert columns["response_time"]["name"] == "response_time"
    assert columns["response_time"]["dtype"] == "float64"
    assert columns["response_time"]["null_count"] == 1
    assert columns["response_time"]["null_percentage"] > 0
    assert columns["response_time"]["cardinality"] == 2
    assert columns["response_time"]["semantic_role"] == "performance_metric"
    assert columns["response_time"]["is_primary_metric"] is True
    assert columns["created_at"]["is_time_axis"] is True


def test_latest_analyses_are_ordered_by_created_at(tmp_path):
    store = KnowledgeGraphStore(tmp_path / "kg.json")
    store.upsert_node(KnowledgeNode(
        "analysis_run:old",
        "analysis_run",
        "Analisi vecchia",
        {"created_at": "2026-01-01T10:00:00"},
    ))
    store.upsert_node(KnowledgeNode(
        "analysis_run:new",
        "analysis_run",
        "Analisi nuova",
        {"created_at": "2026-01-03T10:00:00"},
    ))
    store.save()

    latest = KnowledgeGraphQueryEngine(path=tmp_path / "kg.json").get_latest_analysis_runs(limit=2)

    assert [run["id"] for run in latest] == ["analysis_run:new", "analysis_run:old"]


def test_analysis_lineage_returns_connected_elements(tmp_path):
    snapshot = map_analysis_context(_context())
    run_id = next(node.id for node in snapshot.nodes if node.type == "analysis_run")
    _save_snapshot(tmp_path / "kg.json", snapshot)

    lineage = KnowledgeGraphQueryEngine(path=tmp_path / "kg.json").get_analysis_lineage(run_id)

    assert lineage["analysis_run"]["id"] == run_id
    assert lineage["dataset"][0]["type"] == "dataset"
    assert {column["label"] for column in lineage["columns"]} == {"created_at", "response_time", "status"}
    assert lineage["insights"][0]["type"] == "insight"
    assert lineage["anomalies"][0]["id"] == "anomaly:a-response-time"
    assert lineage["root_causes"][0]["id"] == "root_cause:rc-backlog"
    assert lineage["reports"][0]["type"] == "report"


def test_ultima_analisi_question_returns_deterministic_answer(tmp_path):
    snapshot = map_analysis_context(_context("Ultima analisi response_time"))
    _save_snapshot(tmp_path / "kg.json", snapshot)

    answer = KnowledgeGraphQueryEngine(path=tmp_path / "kg.json").answer_question_deterministic(
        "qual è l'ultima analisi?"
    )

    assert answer["execution_type"] == "deterministic_kg_query"
    assert answer["confidence"] > 0.5
    assert answer["matches"][0]["type"] == "analysis_run"
    assert "ultima analisi" in answer["answer"]


def test_lineage_supports_legacy_and_explicit_relationships(tmp_path):
    store = KnowledgeGraphStore(tmp_path / "kg.json")
    store.upsert_node(KnowledgeNode("analysis_run:r1", "analysis_run", "Run", {"created_at": "2026"}))
    store.upsert_node(KnowledgeNode("dataset:r1", "dataset", "Dataset", {}))
    store.upsert_node(KnowledgeNode("insight:r1", "insight", "Insight", {}))
    store.upsert_edge(KnowledgeEdge("analysis_run:r1", "dataset:r1", "USES_DATASET"))
    store.upsert_edge(KnowledgeEdge("analysis_run:r1", "insight:r1", "GENERATED_INSIGHT"))
    store.save()

    lineage = KnowledgeGraphQueryEngine(path=tmp_path / "kg.json").get_analysis_lineage("analysis_run:r1")

    assert lineage["dataset"][0]["id"] == "dataset:r1"
    assert lineage["insights"][0]["id"] == "insight:r1"
