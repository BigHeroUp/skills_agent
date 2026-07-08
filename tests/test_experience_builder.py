from services.experience import ExperienceBuilder
from services.knowledge_graph.models import KnowledgeEdge, KnowledgeNode
from services.knowledge_graph.query_engine import KnowledgeGraphQueryEngine
from services.knowledge_graph.store import KnowledgeGraphStore


def _build_experience_graph(path):
    store = KnowledgeGraphStore(path)
    for index in range(2):
        run_id = f"analysis_run:run-{index}"
        dataset_id = f"dataset:run-{index}"
        column_id = f"dataframe_column:run-{index}:response_time"
        anomaly_id = f"anomaly:a{index}"
        root_cause_id = f"root_cause:rc{index}"
        store.upsert_node(KnowledgeNode(run_id, "analysis_run", f"Run {index}", {
            "created_at": f"2026-01-0{index + 1}T10:00:00",
            "primary_metric": "response_time",
            "time_axis": "created_at",
            "source_type": "excel",
        }))
        store.upsert_node(KnowledgeNode(dataset_id, "dataset", "performance.xlsx", {
            "source_type": "excel",
            "row_count": 100,
            "column_count": 2,
        }))
        store.upsert_node(KnowledgeNode(column_id, "dataframe_column", "response_time", {
            "dtype": "float64",
            "is_primary_metric": True,
        }))
        store.upsert_node(KnowledgeNode(anomaly_id, "anomaly", "sla_violation", {
            "affected_column": "response_time",
        }))
        store.upsert_node(KnowledgeNode(root_cause_id, "root_cause", "Performance degradation infrastrutturale", {
            "affected_metrics": ["response_time"],
        }))
        store.upsert_edge(KnowledgeEdge(run_id, dataset_id, "USES_DATASET"))
        store.upsert_edge(KnowledgeEdge(run_id, column_id, "HAS_COLUMN"))
        store.upsert_edge(KnowledgeEdge(run_id, anomaly_id, "DETECTED_ANOMALY"))
        store.upsert_edge(KnowledgeEdge(run_id, root_cause_id, "IDENTIFIED_ROOT_CAUSE"))
    store.save()
    return store


def test_builder_creates_experience_from_simulated_analysis_runs(tmp_path):
    store = _build_experience_graph(tmp_path / "kg.json")
    builder = ExperienceBuilder(query_engine=KnowledgeGraphQueryEngine(path=store.path))

    experiences = builder.build_from_latest_analyses(limit=20)
    ids = {item.id for item in experiences}

    assert "experience.metric.response_time" in ids
    assert "experience.anomaly.sla_violation" in ids
    assert "experience.root_cause.performance_degradation_infrastrutturale" in ids
    metric_experience = next(item for item in experiences if item.id == "experience.metric.response_time")
    assert "Analizzare il trend temporale di response_time su created_at" in metric_experience.recommended_steps
    assert "Calcolare percentili e distribuzione di response_time" in metric_experience.recommended_steps


def test_builder_handles_empty_graph_and_runs_without_metric(tmp_path):
    empty_builder = ExperienceBuilder(query_engine=KnowledgeGraphQueryEngine(path=tmp_path / "empty.json"))
    assert empty_builder.build_from_latest_analyses(limit=20) == []

    store = KnowledgeGraphStore(tmp_path / "kg_without_metric.json")
    store.upsert_node(KnowledgeNode("analysis_run:run-1", "analysis_run", "Run 1", {
        "created_at": "2026-01-01T10:00:00",
        "source_type": "excel",
    }))
    store.save()

    builder = ExperienceBuilder(query_engine=KnowledgeGraphQueryEngine(path=store.path))
    experiences = builder.build_from_latest_analyses(limit=20)

    assert experiences == []
