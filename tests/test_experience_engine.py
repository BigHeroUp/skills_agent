from services.experience import AnalyticalExperienceEngine
from services.knowledge_graph.models import KnowledgeEdge, KnowledgeNode
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


def test_engine_finds_relevant_experiences_for_current_profile(tmp_path):
    kg_path = tmp_path / "kg.json"
    experience_path = tmp_path / "experience_store.json"
    _build_experience_graph(kg_path)
    engine = AnalyticalExperienceEngine(experience_path=experience_path, kg_path=kg_path)
    engine.refresh_experience_from_kg(limit=20)

    relevant = engine.find_relevant_experiences(
        {
            "primary_metric": "response_time",
            "column_names": ["response_time", "status"],
            "anomalies": ["sla_violation"],
            "root_causes": ["Performance degradation infrastrutturale"],
            "tags": ["metric"],
        }
    )

    assert relevant["experiences"]
    assert relevant["experiences"][0]["score"] > 0.0
    assert relevant["experiences"][0]["reasons"]


def test_engine_recommendations_are_ordered_by_priority_and_confidence(tmp_path):
    kg_path = tmp_path / "kg.json"
    experience_path = tmp_path / "experience_store.json"
    _build_experience_graph(kg_path)
    engine = AnalyticalExperienceEngine(experience_path=experience_path, kg_path=kg_path)
    engine.refresh_experience_from_kg(limit=20)

    recommendations = engine.recommend_from_experience(
        {
            "primary_metric": "response_time",
            "anomalies": ["sla_violation"],
            "root_causes": ["Performance degradation infrastrutturale"],
        }
    )["recommendations"]

    assert recommendations
    assert recommendations[0]["priority"] == "high"
    assert recommendations == sorted(
        recommendations,
        key=lambda item: (
            {"high": 0, "medium": 1, "low": 2}.get(item["priority"], 99),
            -float(item["confidence"]),
            item["step"],
        ),
    )


def test_engine_handles_empty_profile_and_empty_summary(tmp_path):
    engine = AnalyticalExperienceEngine(
        experience_path=tmp_path / "experience_store.json",
        kg_path=tmp_path / "kg.json",
    )

    relevant = engine.find_relevant_experiences({})
    summary = engine.get_experience_summary()

    assert relevant["status"] == "insufficient_profile"
    assert relevant["experiences"] == []
    assert summary["status"] == "empty"
    assert "Nessuna esperienza" in summary["message"]
