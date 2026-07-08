from core.kernel.bootstrap import create_default_kernel
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


def test_experience_query_capability_works_via_kernel_and_bootstrap(tmp_path):
    kg_path = tmp_path / "kg.json"
    experience_path = tmp_path / "experience_store.json"
    _build_experience_graph(kg_path)
    AnalyticalExperienceEngine(experience_path=experience_path, kg_path=kg_path).refresh_experience_from_kg(limit=20)

    kernel = create_default_kernel(path=kg_path, experience_path=experience_path)
    response = kernel.execute_capability(
        "experience.query",
        payload={
            "question": "cosa abbiamo imparato sui response_time?",
            "mode": "deterministic",
        },
    )

    assert kernel.registry.has("experience.query") is True
    assert response.success is True
    assert response.result["execution_type"] == "deterministic_experience_query"
    assert response.result["confidence"] >= 0.0
