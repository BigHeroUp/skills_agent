from services.knowledge_graph.analysis_comparator import AnalysisComparator, summarize_comparison
from services.knowledge_graph.models import KnowledgeEdge, KnowledgeNode
from services.knowledge_graph.query_engine import KnowledgeGraphQueryEngine
from services.knowledge_graph.store import KnowledgeGraphStore


def _build_comparison_store(path):
    store = KnowledgeGraphStore(path)
    nodes = [
        KnowledgeNode(
            "analysis_run:old",
            "analysis_run",
            "Analisi precedente",
            {
                "created_at": "2026-01-01T10:00:00",
                "primary_metric": "response_time",
                "time_axis": "created_at",
                "confidence_score": 0.7,
            },
        ),
        KnowledgeNode(
            "analysis_run:new",
            "analysis_run",
            "Analisi recente",
            {
                "created_at": "2026-01-02T10:00:00",
                "primary_metric": "response_time",
                "time_axis": "created_at",
                "confidence_score": 0.85,
            },
        ),
        KnowledgeNode("dataset:old", "dataset", "tickets_old.xlsx", {}),
        KnowledgeNode("dataset:new", "dataset", "tickets_new.xlsx", {}),
        KnowledgeNode("column:old:response_time", "dataframe_column", "response_time", {}),
        KnowledgeNode("column:old:status", "dataframe_column", "status", {}),
        KnowledgeNode("column:new:response_time", "dataframe_column", "response_time", {}),
        KnowledgeNode("column:new:priority", "dataframe_column", "priority", {}),
        KnowledgeNode("insight:old", "insight", "baseline_response_time", {}),
        KnowledgeNode("insight:new", "insight", "baseline_response_time", {}),
        KnowledgeNode("anomaly:old", "anomaly", "sla_violation", {"affected_column": "queue_time"}),
        KnowledgeNode("anomaly:new", "anomaly", "numeric_outlier", {"affected_column": "response_time"}),
        KnowledgeNode("root_cause:old", "root_cause", "Backlog storico", {"affected_metrics": ["queue_time"]}),
        KnowledgeNode("root_cause:new", "root_cause", "Saturazione recente", {"affected_metrics": ["response_time"]}),
        KnowledgeNode("report:old", "report", "final_report", {}),
        KnowledgeNode("report:new", "report", "final_report", {}),
    ]
    edges = [
        KnowledgeEdge("analysis_run:old", "dataset:old", "ANALYZED_DATASET"),
        KnowledgeEdge("analysis_run:new", "dataset:new", "ANALYZED_DATASET"),
        KnowledgeEdge("analysis_run:old", "column:old:response_time", "HAS_COLUMN"),
        KnowledgeEdge("analysis_run:old", "column:old:status", "HAS_COLUMN"),
        KnowledgeEdge("analysis_run:new", "column:new:response_time", "HAS_COLUMN"),
        KnowledgeEdge("analysis_run:new", "column:new:priority", "HAS_COLUMN"),
        KnowledgeEdge("analysis_run:old", "insight:old", "PRODUCED_INSIGHT"),
        KnowledgeEdge("analysis_run:new", "insight:new", "PRODUCED_INSIGHT"),
        KnowledgeEdge("analysis_run:old", "anomaly:old", "DETECTED_ANOMALY"),
        KnowledgeEdge("analysis_run:new", "anomaly:new", "DETECTED_ANOMALY"),
        KnowledgeEdge("analysis_run:old", "root_cause:old", "IDENTIFIED_ROOT_CAUSE"),
        KnowledgeEdge("analysis_run:new", "root_cause:new", "IDENTIFIED_ROOT_CAUSE"),
        KnowledgeEdge("analysis_run:old", "report:old", "GENERATED_REPORT"),
        KnowledgeEdge("analysis_run:new", "report:new", "GENERATED_REPORT"),
    ]
    for node in nodes:
        store.upsert_node(node)
    for edge in edges:
        store.upsert_edge(edge)
    store.save()
    return store


def test_compare_analysis_runs_detects_added_and_removed_columns(tmp_path):
    _build_comparison_store(tmp_path / "kg.json")
    engine = KnowledgeGraphQueryEngine(path=tmp_path / "kg.json")

    comparison = AnalysisComparator(engine).compare_analysis_runs("analysis_run:old", "analysis_run:new")

    assert comparison["columns"]["common"] == ["response_time"]
    assert comparison["columns"]["added"] == ["priority"]
    assert comparison["columns"]["removed"] == ["status"]
    assert comparison["primary_metric"]["changed"] is False
    assert comparison["time_axis"]["changed"] is False
    assert comparison["confidence_score"]["delta"] == 0.15


def test_compare_analysis_runs_detects_new_and_removed_anomalies(tmp_path):
    _build_comparison_store(tmp_path / "kg.json")
    engine = KnowledgeGraphQueryEngine(path=tmp_path / "kg.json")

    comparison = engine.compare_latest_analysis_runs()

    assert comparison["anomalies"]["new"] == ["numeric_outlier:response_time"]
    assert comparison["anomalies"]["resolved"] == ["sla_violation:queue_time"]
    assert comparison["root_causes"]["new"] == ["Saturazione recente:response_time"]
    assert comparison["root_causes"]["removed"] == ["Backlog storico:queue_time"]


def test_summarize_comparison_returns_italian_summary(tmp_path):
    _build_comparison_store(tmp_path / "kg.json")
    comparison = KnowledgeGraphQueryEngine(path=tmp_path / "kg.json").compare_latest_analysis_runs()

    summary = summarize_comparison(comparison)

    assert "Confronto deterministico" in summary
    assert "Sintesi differenze" in summary
    assert "Nuove anomalie" in summary
    assert "Anomalie non piu presenti" in summary
    assert "Possibili evoluzioni del fenomeno" in summary


def test_deterministic_query_confronta_ultime_analisi(tmp_path):
    _build_comparison_store(tmp_path / "kg.json")
    engine = KnowledgeGraphQueryEngine(path=tmp_path / "kg.json")

    answer = engine.answer_question_deterministic("confronta ultime analisi")

    assert answer["execution_type"] == "deterministic_kg_query"
    assert answer["confidence"] > 0.5
    assert answer["comparison"]["status"] == "computed"
    assert "Confronto deterministico" in answer["answer"]
    assert [match["id"] for match in answer["matches"]] == ["analysis_run:old", "analysis_run:new"]
