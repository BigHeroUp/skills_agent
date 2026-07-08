from services.experience import AnalyticalExperienceEngine, query_experience
from services.knowledge_graph.models import KnowledgeEdge, KnowledgeNode
from services.knowledge_graph.store import KnowledgeGraphStore
from scripts import query_experience as query_experience_cli
from scripts import refresh_experience as refresh_experience_cli


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


def test_query_recognizes_cases_and_learning_questions(tmp_path):
    kg_path = tmp_path / "kg.json"
    experience_path = tmp_path / "experience_store.json"
    _build_experience_graph(kg_path)
    engine = AnalyticalExperienceEngine(experience_path=experience_path, kg_path=kg_path)
    engine.refresh_experience_from_kg(limit=20)

    similar = query_experience("mostrami i casi simili su response_time", engine=engine)
    learned = query_experience("cosa abbiamo imparato sui response_time?", engine=engine)

    assert similar["success"] is True
    assert similar["matches"]
    assert learned["success"] is True
    assert "esperienze" in learned["answer"].lower() or "trovato" in learned["answer"].lower()


def test_query_filters_specific_metric_and_handles_empty_store(tmp_path):
    empty_engine = AnalyticalExperienceEngine(
        experience_path=tmp_path / "empty_experience_store.json",
        kg_path=tmp_path / "empty_kg.json",
    )
    empty_result = query_experience("casi simili su response_time", engine=empty_engine)
    assert "Non ci sono ancora esperienze" in empty_result["answer"]

    kg_path = tmp_path / "kg.json"
    experience_path = tmp_path / "experience_store.json"
    _build_experience_graph(kg_path)
    engine = AnalyticalExperienceEngine(experience_path=experience_path, kg_path=kg_path)
    engine.refresh_experience_from_kg(limit=20)

    result = query_experience("mostrami i casi simili su response_time", engine=engine)

    assert result["matches"]
    assert all("response_time" in item.get("metrics", []) for item in result["matches"])


def test_cli_behavior_minimum_without_subprocess(tmp_path, monkeypatch, capsys):
    kg_path = tmp_path / "kg.json"
    experience_path = tmp_path / "experience_store.json"
    _build_experience_graph(kg_path)

    monkeypatch.setattr(refresh_experience_cli.KnowledgeGraphStore, "DEFAULT_PATH", kg_path)
    monkeypatch.setattr(refresh_experience_cli.ExperienceStore, "DEFAULT_PATH", experience_path)
    monkeypatch.setattr(query_experience_cli.KnowledgeGraphStore, "DEFAULT_PATH", kg_path)
    monkeypatch.setattr(query_experience_cli.ExperienceStore, "DEFAULT_PATH", experience_path)

    refresh_exit_code = refresh_experience_cli.main(["--limit", "20"])
    refresh_output = capsys.readouterr().out
    query_exit_code = query_experience_cli.main([])
    query_usage_output = capsys.readouterr().out
    valid_query_exit_code = query_experience_cli.main(["casi", "simili", "su", "response_time"])
    valid_query_output = capsys.readouterr().out

    assert refresh_exit_code == 0
    assert "Experience refresh completato" in refresh_output
    assert query_exit_code == 1
    assert "Uso:" in query_usage_output
    assert valid_query_exit_code == 0
    assert "Tipo esecuzione: deterministic_experience_query" in valid_query_output
