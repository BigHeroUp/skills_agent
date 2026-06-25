import json

from services.analysis_session_manager import AnalysisSessionManager
from services.pattern_knowledge_engine import PatternKnowledgeEngine
from services.senior_data_analyst_engine import SeniorDataAnalystEngine


def _pattern_ids(patterns):
    return {pattern["pattern_id"] for pattern in patterns}


def test_detects_time_performance_analysis():
    engine = PatternKnowledgeEngine()

    patterns = engine.detect_patterns(
        "Analizza tempo di risoluzione, P95, outlier e rispetto SLA",
        {
            "columns": ["created_at", "resolved_at", "duration_hours"],
            "numeric_columns": ["duration_hours"],
            "datetime_columns": ["created_at", "resolved_at"],
        },
    )

    assert "time_performance_analysis" in _pattern_ids(patterns)


def test_detects_categorical_segmentation():
    patterns = PatternKnowledgeEngine().detect_patterns(
        "Segmenta i ticket per stato e mostra i top valori",
        {"categorical_columns": ["stato", "categoria"]},
    )

    assert "categorical_segmentation" in _pattern_ids(patterns)


def test_detects_data_quality_audit():
    patterns = PatternKnowledgeEngine().detect_patterns(
        "Esegui un audit di qualita su null, duplicati e formati data",
        {"missing_values": {"owner": {"count": 3}}, "duplicate_rows": 2},
    )

    assert "data_quality_audit" in _pattern_ids(patterns)


def test_detects_operational_kpi_analysis():
    patterns = PatternKnowledgeEngine().detect_patterns(
        "Prepara una panoramica dei KPI operativi e del loro andamento",
        {
            "numeric_columns": ["volume", "costo"],
            "datetime_columns": ["data"],
        },
    )

    assert "operational_kpi_analysis" in _pattern_ids(patterns)


def test_suggests_analysis_steps_in_priority_order():
    engine = PatternKnowledgeEngine()
    patterns = engine.detect_patterns(
        "Analizza durata, SLA e anomalie per categoria"
    )

    steps = engine.suggest_analysis_steps(patterns)

    assert steps
    assert steps == sorted(steps, key=lambda item: (item["priority"], item["step_id"]))
    assert all(step["pattern_id"] for step in steps)
    assert any(step["analysis_type"] == "time_trend" for step in steps)


def test_enriches_analysis_plan_without_replacing_base_plan():
    engine = PatternKnowledgeEngine()
    base_plan = {
        "analysis_type": "time_trend",
        "time_column": "created_at",
        "aggregation": "count",
    }

    enriched = engine.enrich_analysis_plan(
        base_plan,
        "Analizza performance temporale e rispetto SLA",
        {"datetime_columns": ["created_at"], "numeric_columns": ["duration"]},
    )

    assert enriched["analysis_type"] == "time_trend"
    assert enriched["time_column"] == "created_at"
    knowledge = enriched["knowledge_enrichment"]
    assert "time_performance_analysis" in knowledge["detected_pattern_ids"]
    assert "p95" in knowledge["recommended_metrics"]
    assert knowledge["senior_analyst_notes"]
    assert "knowledge_enrichment" not in base_plan


def test_export_knowledge_base_is_json_serializable():
    knowledge_base = PatternKnowledgeEngine().export_knowledge_base()

    assert knowledge_base["schema_version"] == 1
    assert knowledge_base["storage"] == "memory"
    assert knowledge_base["pattern_count"] == 4
    assert all(
        {
            "pattern_id",
            "name",
            "description",
            "trigger_keywords",
            "recommended_metrics",
            "recommended_groupings",
            "recommended_charts",
            "senior_analyst_notes",
            "confidence_score",
        }.issubset(pattern)
        for pattern in knowledge_base["patterns"]
    )
    json.dumps(knowledge_base)


def test_session_manager_saves_detected_patterns_in_iteration():
    manager = AnalysisSessionManager(id_factory=lambda: "session-pattern")
    session = manager.start_session(
        "Analizza i ticket",
        "csv",
        {
            "columns": ["stato", "created_at"],
            "categorical_columns": ["stato"],
            "datetime_columns": ["created_at"],
        },
    )

    iteration = manager.add_iteration(
        session["session_id"],
        "Segmenta i ticket per stato",
        {
            "analysis_plan": {"analysis_type": "count_occurrences"},
            "deterministic_results": {"counts": []},
        },
    )
    context = manager.build_context_for_next_iteration(session["session_id"])

    assert "categorical_segmentation" in _pattern_ids(
        iteration["detected_patterns"]
    )
    assert context["latest_detected_patterns"] == iteration["detected_patterns"]


def test_senior_report_includes_pattern_methodology_and_recommendations():
    patterns = PatternKnowledgeEngine().detect_patterns(
        "Analizza tempo di risoluzione e rispetto SLA"
    )
    analysis = SeniorDataAnalystEngine().analyze({
        "deterministic_summary": {
            "status": "computed",
            "row_count": 10,
            "column_count": 2,
            "columns": ["duration_hours", "created_at"],
            "numeric_columns": ["duration_hours"],
            "datetime_columns": ["created_at"],
            "categorical_columns": [],
            "numeric_summary": {},
            "missing_values": {},
            "duplicate_rows": 0,
        },
        "detected_patterns": patterns,
    })

    assert analysis["methodological_notes"]
    assert any(
        "P75/P90/P95/P99" in recommendation
        for recommendation in analysis["operational_recommendations"]
    )
    assert "Best practice metodologiche" in analysis["final_report"]
