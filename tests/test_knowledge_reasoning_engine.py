from __future__ import annotations

from datetime import datetime

import pandas as pd

from agents.knowledge_reasoning_agent import KnowledgeReasoningAgent
from services.knowledge_graph.analysis_mapper import map_analysis_context
from services.knowledge_graph.reasoning_engine import (
    KnowledgeReasoningEngine,
    build_dataset_profile_from_context,
)
from services.knowledge_graph.store import KnowledgeGraphStore
from services.senior_data_analyst_engine import SeniorDataAnalystEngine
from utils.context import AgentContext


def _build_context(
    user_input: str,
    created_at: datetime,
    source_type: str = "excel",
    metric: str = "response_time",
    time_axis: str = "created_at",
    rows: int = 4,
) -> AgentContext:
    dataframe = pd.DataFrame(
        {
            "created_at": pd.date_range("2026-01-01", periods=rows, freq="D"),
            "response_time": [120.0, 135.0, 141.0, 160.0][:rows],
            "status": ["ok", "warning", "ok", "ko"][:rows],
            "channel": ["web", "app", "web", "store"][:rows],
        }
    )
    context = AgentContext(
        user_input=user_input,
        raw_data={"dataframe": dataframe},
        metadata={"source_type": source_type, "filename": "performance.xlsx"},
    )
    context.created_at = created_at
    context.primary_metric = metric
    context.time_axis = time_axis
    context.semantic_columns = {
        "created_at": {"semantic_role": "time_axis"},
        "response_time": {"semantic_role": "performance_metric"},
        "status": {"semantic_role": "status_dimension"},
        "channel": {"semantic_role": "channel_dimension"},
    }
    context.insights = {
        "operational_recommendations": [
            "Verificare backlog operativo sui segmenti con response_time elevato"
        ],
        "analysis_report": "# Report business",
    }
    context.anomaly_detection_results = {
        "anomalies": [
            {
                "anomaly_id": f"a-{created_at:%H%M%S}",
                "anomaly_type": "sla_violation",
                "severity": "high",
                "confidence_score": 0.85,
                "affected_column": metric,
            }
        ]
    }
    context.root_cause_results = {
        "possible_causes": [
            {
                "cause_id": f"rc-{created_at:%H%M%S}",
                "title": "Performance degradation da backlog operativo",
                "severity": "high",
                "confidence_score": 0.72,
                "affected_metrics": [metric],
                "related_anomalies": [f"a-{created_at:%H%M%S}"],
            }
        ]
    }
    context.final_report = "# Report\nAnalisi completata."
    return context


def _save_contexts(path, contexts: list[AgentContext]) -> None:
    store = KnowledgeGraphStore(path)
    for context in contexts:
        snapshot = map_analysis_context(context)
        for node in snapshot.nodes:
            store.upsert_node(node)
        for edge in snapshot.edges:
            store.upsert_edge(edge)
    store.save()


def test_build_dataset_profile_from_context_avoids_raw_rows():
    context = _build_context(
        "Analizza response_time per stato e canale",
        created_at=datetime(2026, 1, 10, 9, 0, 0),
    )

    profile = build_dataset_profile_from_context(context)

    assert profile["row_count"] == 4
    assert profile["column_count"] == 4
    assert profile["primary_metric"] == "response_time"
    assert profile["time_axis"] == "created_at"
    assert profile["column_names"] == ["created_at", "response_time", "status", "channel"]
    assert "120.0" not in profile["detected_keywords"]
    assert "135.0" not in str(profile)
    assert "141.0" not in str(profile)


def test_build_dataset_profile_from_context_without_dataframe():
    context = AgentContext(
        user_input="Analizza response_time",
        raw_data={},
        metadata={"source_type": "excel"},
    )
    context.primary_metric = "response_time"

    profile = build_dataset_profile_from_context(context)

    assert profile["row_count"] == 0
    assert profile["column_count"] == 0
    assert profile["column_names"] == []
    assert profile["dtypes"] == {}


def test_build_dataset_profile_from_context_with_empty_dataframe():
    context = AgentContext(
        user_input="Analizza response_time",
        raw_data={"dataframe": pd.DataFrame(columns=["created_at", "response_time"])},
        metadata={"source_type": "excel"},
    )

    profile = build_dataset_profile_from_context(context)

    assert profile["row_count"] == 0
    assert profile["column_count"] == 2
    assert profile["column_names"] == ["created_at", "response_time"]


def test_reasoning_engine_handles_empty_graph_and_empty_profile(tmp_path):
    engine = KnowledgeReasoningEngine(path=tmp_path / "empty.json")

    result = engine.build_reasoning_context_for_analysis({})

    assert result["similarity"]["similar_runs"] == []
    assert result["reusable_patterns"]["reusable_patterns"]["metrics"] == []
    assert result["recommendations"]["recommended_steps"] == []
    assert "Non sono state trovate analisi storiche" in result["reasoning_summary"]


def test_reasoning_engine_finds_similar_runs_and_patterns(tmp_path):
    current = _build_context(
        "Analizza response_time per stato",
        created_at=datetime(2026, 2, 10, 10, 0, 0),
    )
    similar_a = _build_context(
        "Analizza response_time per stato e canale",
        created_at=datetime(2026, 1, 10, 10, 0, 0),
    )
    similar_b = _build_context(
        "Analizza response_time e trend temporale",
        created_at=datetime(2026, 1, 8, 10, 0, 0),
    )
    different = _build_context(
        "Analizza revenue mensile",
        created_at=datetime(2025, 12, 1, 10, 0, 0),
        source_type="csv",
        metric="revenue",
        time_axis="month",
    )
    different.raw_data["dataframe"] = pd.DataFrame(
        {
            "month": pd.date_range("2026-01-01", periods=4, freq="MS"),
            "revenue": [1000, 1100, 900, 1500],
            "segment": ["a", "b", "a", "c"],
        }
    )
    different.semantic_columns = {
        "month": {"semantic_role": "time_axis"},
        "revenue": {"semantic_role": "business_metric"},
        "segment": {"semantic_role": "segment_dimension"},
    }
    path = tmp_path / "kg.json"
    _save_contexts(path, [similar_a, similar_b, different])

    engine = KnowledgeReasoningEngine(path=path)
    reasoning = engine.build_reasoning_context_for_analysis(
        build_dataset_profile_from_context(current)
    )

    similar_runs = reasoning["similarity"]["similar_runs"]
    assert similar_runs
    assert similar_runs == sorted(similar_runs, key=lambda item: item["score"], reverse=True)
    assert "response_time" in reasoning["reusable_patterns"]["reusable_patterns"]["metrics"]
    assert "sla_violation" in reasoning["reusable_patterns"]["reusable_patterns"]["anomalies"]
    assert reasoning["recommendations"]["recommended_steps"]
    assert reasoning["execution_type"] == "deterministic_knowledge_reasoning"
    assert all(0.0 <= item["score"] <= 1.0 for item in similar_runs)
    assert all(item["reasons"] for item in similar_runs if item["score"] > 0)


def test_reasoning_engine_handles_empty_current_profile(tmp_path):
    context = _build_context(
        "Analizza response_time per stato e canale",
        created_at=datetime(2026, 1, 10, 10, 0, 0),
    )
    path = tmp_path / "kg.json"
    _save_contexts(path, [context])

    engine = KnowledgeReasoningEngine(path=path)
    result = engine.find_similar_analysis_runs({})

    assert result["similar_runs"] == []


def test_knowledge_reasoning_agent_is_non_blocking_on_failure():
    agent = KnowledgeReasoningAgent.__new__(KnowledgeReasoningAgent)
    agent.name = "KnowledgeReasoning"
    agent.logger = type("Logger", (), {"warning": lambda *args, **kwargs: None})()
    agent.log = lambda message: None

    class _BrokenEngine:
        def build_reasoning_context_for_analysis(self, current_profile):
            raise RuntimeError("kg unavailable")

    agent.reasoning_engine = _BrokenEngine()

    context = _build_context(
        "Analizza response_time per stato",
        created_at=datetime(2026, 2, 11, 11, 0, 0),
    )
    context.is_valid = False
    result = agent.process(context)

    assert result.errors == []
    assert result.knowledge_reasoning_context["status"] == "skipped"
    assert result.recommended_analytical_steps == []
    assert result.is_valid is False


def test_report_can_include_memory_based_recommendations():
    processed_data = {
        "deterministic_summary": {
            "row_count": 10,
            "column_count": 4,
            "numeric_summary": {
                "response_time": {
                    "count": 10,
                    "mean": 140.0,
                    "median": 130.0,
                    "min": 90.0,
                    "max": 400.0,
                    "missing": 0,
                }
            },
            "categorical_summary": {
                "status": {"unique": 3, "top_values": {"ok": 6, "ko": 2, "warning": 2}, "missing": 0}
            },
            "time_ranges": {
                "created_at": {
                    "min": "2026-01-01T00:00:00",
                    "max": "2026-01-10T00:00:00",
                    "valid_values": 10,
                }
            },
        },
        "analysis_plan": {"analysis_type": "time_trend"},
        "deterministic_results": {"analysis_type": "time_trend", "points": []},
        "recommended_analytical_steps": [
            {
                "step": "Confrontare i risultati correnti con analisi simili gia archiviate",
                "reason": "Esistono run storiche con metrica e colonne simili.",
                "priority": "medium",
                "source": "similar_runs",
            }
        ],
    }

    report = SeniorDataAnalystEngine().analyze(
        processed_data,
        user_request="Analizza response_time",
    )["final_report"]

    assert "## Raccomandazioni basate sulla memoria analitica" in report
    assert "analisi simili gia archiviate" in report


def test_report_without_memory_recommendations_hides_optional_section():
    processed_data = {
        "deterministic_summary": {
            "row_count": 5,
            "column_count": 2,
            "numeric_summary": {"response_time": {"count": 5, "mean": 10.0, "median": 10.0, "missing": 0}},
            "categorical_summary": {},
            "time_ranges": {},
        },
        "analysis_plan": {"analysis_type": "distribution"},
        "deterministic_results": {"analysis_type": "distribution"},
        "recommended_analytical_steps": [],
    }

    report = SeniorDataAnalystEngine().analyze(processed_data)["final_report"]

    assert "## Raccomandazioni basate sulla memoria analitica" not in report
