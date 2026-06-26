import json

import pandas as pd

import agents.data_processor as data_processor_module
from agents.data_processor import DataProcessorAgent
from services.analysis_session_manager import AnalysisSessionManager
from services.analytical_reasoning_layer import AnalyticalReasoningLayer
from services.pattern_knowledge_engine import PatternKnowledgeEngine
from utils.analysis_history_manager import AnalysisHistoryManager
from utils.context import AgentContext


def _layer():
    return AnalyticalReasoningLayer()


def test_strategy_for_time_performance_analysis_prioritizes_percentiles_trend_outliers():
    metadata = {
        "columns": ["created_at", "duration_hours", "status"],
        "numeric_columns": ["duration_hours"],
        "datetime_columns": ["created_at"],
        "categorical_columns": ["status"],
    }
    patterns = PatternKnowledgeEngine().detect_patterns(
        "Analizza tempi performance SLA e outlier",
        metadata,
    )

    strategy = _layer().build_strategy(
        "Analizza tempi performance SLA e outlier",
        metadata,
        patterns,
    )

    sequence = [step["analysis_type"] for step in strategy["recommended_sequence"]]
    assert sequence[:4] == [
        "percentile_analysis",
        "time_trend",
        "outlier_analysis",
        "threshold_comparison",
    ]
    assert strategy["recommended_sequence"][0]["required_columns"] == ["duration_hours"]
    assert strategy["confidence_score"] > 0


def test_strategy_for_categorical_segmentation_prioritizes_segments_and_top_values():
    metadata = {
        "columns": ["status", "owner", "amount"],
        "numeric_columns": ["amount"],
        "categorical_columns": ["status", "owner"],
        "datetime_columns": [],
    }
    patterns = PatternKnowledgeEngine().detect_patterns(
        "Mostra distribuzione e top valori per status",
        metadata,
    )

    strategy = _layer().build_strategy(
        "Mostra distribuzione e top valori per status",
        metadata,
        patterns,
    )

    sequence = [step["analysis_type"] for step in strategy["recommended_sequence"]]
    assert sequence[:2] == ["categorical_segmentation", "top_values"]
    assert strategy["recommended_sequence"][0]["required_columns"] == ["status"]


def test_ambiguous_request_generates_clarification_questions():
    strategy = _layer().build_strategy(
        "Analizza questi dati",
        {
            "columns": ["status", "amount"],
            "numeric_columns": ["amount"],
            "categorical_columns": ["status"],
            "datetime_columns": [],
        },
    )

    question_ids = {item["question_id"] for item in strategy["clarification_questions"]}
    assert "analysis_goal" in question_ids


def test_excludes_trend_when_datetime_column_is_missing():
    strategy = _layer().build_strategy(
        "Analizza il trend delle performance",
        {
            "columns": ["duration_hours"],
            "numeric_columns": ["duration_hours"],
            "datetime_columns": [],
            "categorical_columns": [],
        },
    )

    excluded = {item["analysis_type"]: item["reason"] for item in strategy["excluded_analyses"]}
    assert "time_trend" in excluded
    assert "Mancano colonne data/ora" in excluded["time_trend"]
    assert "time_trend" not in [
        step["analysis_type"] for step in strategy["recommended_sequence"]
    ]


def test_excludes_numeric_statistics_when_numeric_columns_are_missing():
    strategy = _layer().build_strategy(
        "Analizza percentili e statistiche numeriche",
        {
            "columns": ["status", "owner"],
            "numeric_columns": [],
            "datetime_columns": [],
            "categorical_columns": ["status", "owner"],
        },
    )

    excluded = {item["analysis_type"] for item in strategy["excluded_analyses"]}
    assert "numeric_distribution" in excluded
    assert "percentile_analysis" in excluded
    assert "numeric_distribution" not in [
        step["analysis_type"] for step in strategy["recommended_sequence"]
    ]


def test_ranking_is_influenced_by_learning_state():
    candidates = [
        {
            "analysis_type": "categorical_segmentation",
            "required_columns": ["status"],
            "pattern_id": "categorical_segmentation",
            "base_priority": 20,
            "confidence_score": 0.4,
        },
        {
            "analysis_type": "percentile_analysis",
            "required_columns": ["duration"],
            "pattern_id": "time_performance_analysis",
            "base_priority": 10,
            "confidence_score": 0.4,
        },
    ]
    context = {
        "intent": {"performance": False, "categorical": False, "quality": False},
        "detected_patterns": [],
        "learning_state": {
            "patterns": [
                {
                    "pattern_id": "categorical_segmentation",
                    "confidence_score": 0.95,
                },
                {
                    "pattern_id": "time_performance_analysis",
                    "confidence_score": 0.2,
                },
            ]
        },
    }

    ranked = _layer().rank_candidate_analyses(candidates, context)

    assert ranked[0]["analysis_type"] == "categorical_segmentation"


def test_export_reasoning_trace_is_json_serializable():
    strategy = _layer().build_strategy(
        "Distribuzione per status",
        {
            "columns": ["status"],
            "categorical_columns": ["status"],
            "numeric_columns": [],
            "datetime_columns": [],
        },
    )

    trace = _layer().export_reasoning_trace(strategy)

    json.dumps(trace)
    assert trace["strategy_id"] == strategy["strategy_id"]


def test_analysis_session_manager_stores_strategy_and_reasoning_trace():
    manager = AnalysisSessionManager(id_factory=lambda: "session-arl")
    session = manager.start_session(
        "Analizza ticket",
        "csv",
        {
            "columns": ["created_at", "duration_hours"],
            "numeric_columns": ["duration_hours"],
            "datetime_columns": ["created_at"],
        },
    )

    iteration = manager.add_iteration(
        session["session_id"],
        "Analizza tempi SLA",
        {"analysis_plan": {}, "deterministic_results": {}},
    )

    assert iteration["analytical_strategy"]["strategy_id"]
    assert iteration["analytical_reasoning_trace"]["strategy_id"] == iteration[
        "analytical_strategy"
    ]["strategy_id"]
    context = manager.build_context_for_next_iteration(session["session_id"])
    assert context["latest_analytical_strategy"]["strategy_id"]


def test_data_processor_stores_analytical_strategy_in_processed_data(monkeypatch, tmp_path):
    manager = AnalysisHistoryManager(db_path=tmp_path / "analysis_history.db")
    monkeypatch.setattr(data_processor_module, "AnalysisHistoryManager", lambda: manager)

    agent = DataProcessorAgent.__new__(DataProcessorAgent)
    agent.name = "DataProcessor"
    agent.log = lambda message: None
    agent.build_prompt_with_skill = lambda prompt: prompt
    agent.call_openai = lambda messages: "report deterministico"

    context = AgentContext(
        user_input="Analizza distribuzione ticket per stato",
        raw_data={"dataframe": pd.DataFrame({"stato": ["open", "closed", "open"]})},
        metadata={"source_type": "csv"},
    )

    result = agent.process(context)

    assert result.analytical_strategy["strategy_id"]
    assert result.analytical_reasoning_trace["strategy_id"] == result.analytical_strategy[
        "strategy_id"
    ]
    assert result.processed_data["analytical_strategy"] == result.analytical_strategy
    assert result.processed_data["analytical_reasoning_trace"] == result.analytical_reasoning_trace
