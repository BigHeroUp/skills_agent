import json
from datetime import datetime

from services.analysis_session_manager import AnalysisSessionManager
from services.learning_engine import LearningEngine
from services.pattern_knowledge_engine import PatternKnowledgeEngine


def _engine():
    counter = {"value": 0}

    def id_factory():
        counter["value"] += 1
        return f"event-{counter['value']}"

    return LearningEngine(
        clock=lambda: datetime(2026, 6, 26, 12, 0, 0),
        id_factory=id_factory,
    )


def test_record_usage_creates_stats_and_event():
    result = _engine().record_usage("categorical_segmentation")

    assert result["pattern_id"] == "categorical_segmentation"
    assert result["usage_count"] == 1
    assert result["event"]["event_type"] == "usage"
    assert result["event"]["pattern_id"] == "categorical_segmentation"


def test_record_feedback_utile_increases_confidence():
    engine = _engine()
    before = engine.record_usage("operational_kpi_analysis")["confidence_score"]
    after = engine.record_feedback("operational_kpi_analysis", "utile")

    assert after["success_count"] == 1
    assert after["failure_count"] == 0
    assert after["confidence_score"] > before


def test_record_feedback_non_utile_reduces_confidence():
    engine = _engine()
    before = engine.record_usage("data_quality_audit")["confidence_score"]
    after = engine.record_feedback("data_quality_audit", "non utile")

    assert after["failure_count"] == 1
    assert after["confidence_score"] < before


def test_update_confidence_returns_current_stats():
    engine = _engine()
    engine.record_usage("time_performance_analysis")
    engine.record_feedback("time_performance_analysis", "utile")

    updated = engine.update_confidence("time_performance_analysis")

    assert updated["pattern_id"] == "time_performance_analysis"
    assert updated["confidence_score"] == engine.get_pattern_stats(
        "time_performance_analysis"
    )["confidence_score"]


def test_promotes_pattern_after_repeated_positive_outcomes():
    engine = _engine()
    for _ in range(3):
        engine.record_usage("categorical_segmentation")
        result = engine.record_feedback("categorical_segmentation", "utile")

    assert result["status"] == "promoted"
    assert result["confidence_score"] >= engine.PROMOTION_THRESHOLD


def test_demotes_pattern_after_negative_feedback():
    result = _engine().record_feedback("data_quality_audit", "non utile")

    assert result["status"] == "demoted"
    assert result["confidence_score"] <= LearningEngine.DEMOTION_THRESHOLD


def test_recommend_patterns_orders_by_learned_confidence():
    engine = _engine()
    for _ in range(3):
        engine.record_usage("high")
        engine.record_feedback("high", "utile")
    engine.record_feedback("low", "non utile")

    recommendations = engine.recommend_patterns(
        "analizza metriche operative",
        [
            {"pattern_id": "low", "confidence_score": 0.95},
            {"pattern_id": "high", "confidence_score": 0.1},
        ],
    )

    assert [item["pattern_id"] for item in recommendations] == ["high", "low"]
    assert recommendations[0]["learning"]["status"] == "promoted"


def test_export_learning_state_is_json_serializable():
    engine = _engine()
    engine.record_usage("operational_kpi_analysis", {"source": "test"})
    engine.record_feedback("operational_kpi_analysis", "utile")

    state = engine.export_learning_state()

    assert state["schema_version"] == 1
    assert state["storage"] == "memory"
    assert state["event_count"] == 2
    assert state["persistence"]["target"] == "sqlite"
    json.dumps(state)


def test_analysis_session_manager_stores_learning_events():
    learning_engine = _engine()
    manager = AnalysisSessionManager(
        id_factory=lambda: "session-learning",
        clock=lambda: datetime(2026, 6, 26, 12, 0, 0),
        learning_engine=learning_engine,
    )
    session = manager.start_session(
        "Analizza i ticket",
        "csv",
        {"categorical_columns": ["stato"]},
    )

    iteration = manager.add_iteration(
        session["session_id"],
        "Segmenta i ticket per stato",
        {"analysis_plan": {"analysis_type": "count_occurrences"}},
    )
    context = manager.build_context_for_next_iteration(session["session_id"])

    assert iteration["learning_events"]
    assert iteration["learning_state"]["event_count"] == len(iteration["learning_events"])
    assert context["latest_learning_events"] == iteration["learning_events"]


def test_pattern_knowledge_engine_uses_learning_state_for_ranking():
    learning_engine = _engine()
    for _ in range(3):
        learning_engine.record_usage("operational_kpi_analysis")
        learning_engine.record_feedback("operational_kpi_analysis", "utile")
    learning_engine.record_feedback("categorical_segmentation", "non utile")

    engine = PatternKnowledgeEngine(learning_state=learning_engine.export_learning_state())
    patterns = engine.detect_patterns(
        "Prepara dashboard KPI e segmenta per stato",
        {
            "numeric_columns": ["volume"],
            "categorical_columns": ["stato"],
        },
    )

    assert patterns[0]["pattern_id"] == "operational_kpi_analysis"
    assert patterns[0]["learning"]["status"] == "promoted"
    assert patterns[-1]["pattern_id"] != "operational_kpi_analysis"
