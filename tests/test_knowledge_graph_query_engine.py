from services.knowledge_graph.models import KnowledgeEdge, KnowledgeNode
from services.knowledge_graph.query_engine import KnowledgeGraphQueryEngine
from services.knowledge_graph.store import KnowledgeGraphStore


def _build_store(path):
    store = KnowledgeGraphStore(path)
    nodes = [
        KnowledgeNode(
            id="python_file:utils/chart_generator.py",
            type="python_file",
            label="utils/chart_generator.py",
            properties={"path": "utils/chart_generator.py"},
        ),
        KnowledgeNode(
            id="python_class:utils/chart_generator.py:ChartGenerator",
            type="python_class",
            label="ChartGenerator",
            properties={"file": "utils/chart_generator.py"},
        ),
        KnowledgeNode(
            id="python_function:utils/chart_generator.py:ChartGenerator.generate_dashboard_charts",
            type="python_function",
            label="generate_dashboard_charts",
            properties={"file": "utils/chart_generator.py", "qualname": "ChartGenerator.generate_dashboard_charts"},
        ),
        KnowledgeNode(
            id="python_import:plotly.express",
            type="python_import",
            label="plotly.express",
            properties={"module": "plotly", "imported_name": "express"},
        ),
        KnowledgeNode(
            id="analysis_run:run-1",
            type="analysis_run",
            label="Analisi performance da Excel",
            properties={"source_type": "excel"},
        ),
        KnowledgeNode(
            id="dataset:run-1",
            type="dataset",
            label="performance.xlsx",
            properties={"source_type": "excel", "row_count": 100, "column_count": 2},
        ),
        KnowledgeNode(
            id="dataframe_column:run-1:response_time",
            type="dataframe_column",
            label="response_time",
            properties={"dtype": "float64"},
        ),
        KnowledgeNode(
            id="anomaly:a1",
            type="anomaly",
            label="sla_violation",
            properties={"affected_column": "response_time", "severity": "high"},
        ),
        KnowledgeNode(
            id="root_cause:rc1",
            type="root_cause",
            label="Possibile saturazione operativa",
            properties={"affected_metrics": ["response_time"], "severity": "high"},
        ),
        KnowledgeNode(
            id="report:run-1",
            type="report",
            label="final_report",
            properties={"length_chars": 1200},
        ),
    ]
    edges = [
        KnowledgeEdge("python_file:utils/chart_generator.py", "python_class:utils/chart_generator.py:ChartGenerator", "CONTAINS"),
        KnowledgeEdge(
            "python_class:utils/chart_generator.py:ChartGenerator",
            "python_function:utils/chart_generator.py:ChartGenerator.generate_dashboard_charts",
            "CONTAINS",
        ),
        KnowledgeEdge("python_file:utils/chart_generator.py", "python_import:plotly.express", "IMPORTS"),
        KnowledgeEdge("analysis_run:run-1", "dataset:run-1", "USES_DATASET"),
        KnowledgeEdge("dataset:run-1", "dataframe_column:run-1:response_time", "HAS_COLUMN"),
        KnowledgeEdge("analysis_run:run-1", "anomaly:a1", "DETECTED_ANOMALY"),
        KnowledgeEdge("root_cause:rc1", "anomaly:a1", "EXPLAINS_ANOMALY"),
        KnowledgeEdge("analysis_run:run-1", "report:run-1", "GENERATED_REPORT"),
    ]
    for node in nodes:
        store.upsert_node(node)
    for edge in edges:
        store.upsert_edge(edge)
    store.save()
    return store


def test_find_nodes_edges_and_neighbors(tmp_path):
    _build_store(tmp_path / "kg.json")
    engine = KnowledgeGraphQueryEngine(path=tmp_path / "kg.json")

    nodes = engine.find_nodes(
        node_type="dataset",
        label_contains="performance",
        property_filters={"source_type": "excel"},
    )
    edges = engine.find_edges(relationship="DETECTED_ANOMALY", source="analysis_run:run-1")
    neighbors = engine.get_neighbors("analysis_run:run-1", direction="out")

    assert nodes[0]["label"] == "performance.xlsx"
    assert edges[0]["target"] == "anomaly:a1"
    assert {item["node"]["id"] for item in neighbors} >= {"dataset:run-1", "anomaly:a1", "report:run-1"}


def test_search_code_and_analysis(tmp_path):
    _build_store(tmp_path / "kg.json")
    engine = KnowledgeGraphQueryEngine(path=tmp_path / "kg.json")

    code_matches = engine.search_code("grafici", limit=5)
    analysis_matches = engine.search_analysis("response_time excel", limit=5)

    assert code_matches[0]["type"] == "python_function"
    assert code_matches[0]["label"] == "generate_dashboard_charts"
    assert {match["type"] for match in analysis_matches} >= {"dataset", "dataframe_column", "anomaly"}


def test_answer_question_deterministic_for_code_and_analysis(tmp_path):
    _build_store(tmp_path / "kg.json")
    engine = KnowledgeGraphQueryEngine(path=tmp_path / "kg.json")

    function_answer = engine.answer_question_deterministic("quali funzioni generano grafici?")
    analysis_answer = engine.answer_question_deterministic(
        "quali analisi hanno anomalie su response_time?"
    )

    assert function_answer["execution_type"] == "deterministic_kg_query"
    assert function_answer["confidence"] > 0.5
    assert function_answer["matches"][0]["type"] == "python_function"
    assert function_answer["matches"][0]["label"] == "generate_dashboard_charts"
    assert analysis_answer["matches"][0]["id"] == "analysis_run:run-1"
    assert analysis_answer["matches"][0]["matched_anomaly"]["id"] == "anomaly:a1"


def test_missing_graph_returns_clear_message(tmp_path):
    engine = KnowledgeGraphQueryEngine(path=tmp_path / "missing.json")

    result = engine.answer_question_deterministic("quali file?")

    assert result["matches"] == []
    assert result["confidence"] == 0.0
    assert "Knowledge Graph non trovato" in result["answer"]


def test_reasoning_history_questions_require_sufficient_runs(tmp_path):
    _build_store(tmp_path / "kg.json")
    engine = KnowledgeGraphQueryEngine(path=tmp_path / "kg.json")

    result = engine.answer_question_deterministic("cosa abbiamo fatto in casi simili?")

    assert result["execution_type"] == "deterministic_kg_query"
    assert result["confidence"] <= 0.25
    assert "Non ci sono dati sufficienti" in result["answer"]


def test_reasoning_history_questions_return_patterns_when_available(tmp_path):
    store = KnowledgeGraphStore(tmp_path / "kg.json")
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
        store.upsert_node(KnowledgeNode(root_cause_id, "root_cause", "Backlog operativo", {
            "affected_metrics": ["response_time"],
        }))
        store.upsert_edge(KnowledgeEdge(run_id, dataset_id, "USES_DATASET"))
        store.upsert_edge(KnowledgeEdge(run_id, column_id, "HAS_COLUMN"))
        store.upsert_edge(KnowledgeEdge(run_id, anomaly_id, "DETECTED_ANOMALY"))
        store.upsert_edge(KnowledgeEdge(run_id, root_cause_id, "IDENTIFIED_ROOT_CAUSE"))
    store.save()

    engine = KnowledgeGraphQueryEngine(path=tmp_path / "kg.json")
    result = engine.answer_question_deterministic("mostrami i pattern ricorrenti")

    assert result["confidence"] >= 0.3
    assert "pattern ricorrenti" in result["answer"].lower()
    assert result["reusable_patterns"]["reusable_patterns"]["metrics"] == ["response_time"]


def test_reasoning_history_intent_is_not_triggered_by_generic_analysis_query(tmp_path):
    _build_store(tmp_path / "kg.json")
    engine = KnowledgeGraphQueryEngine(path=tmp_path / "kg.json")

    result = engine.answer_question_deterministic("fammi una analisi del dataset")

    assert "dati sufficienti" not in result["answer"].lower()
    assert result["matches"]
