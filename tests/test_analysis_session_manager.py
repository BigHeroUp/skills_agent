import json

import pytest

from services.analysis_session_manager import AnalysisSessionManager


def _manager():
    return AnalysisSessionManager(id_factory=lambda: "session-001")


def _payload(analysis_type="count_occurrences"):
    return {
        "analysis_plan": {
            "analysis_type": analysis_type,
            "target_column": "stato",
        },
        "deterministic_results": {
            "analysis_type": analysis_type,
            "counts": [{"value": "open", "count": 3}],
        },
        "insights": {
            "key_findings": ["Open e lo stato piu frequente."],
        },
        "final_report": "# Report\nRisultato locale.",
    }


def test_start_session_creates_json_serializable_record():
    session = _manager().start_session(
        user_request="Analizza i ticket",
        source_type="CSV",
        dataframe_metadata={"rows": 10, "columns": ["stato", "created_at"]},
    )

    assert session["session_id"] == "session-001"
    assert session["source_type"] == "csv"
    assert session["iteration_count"] == 0
    assert session["iterations"] == []
    json.dumps(session)


def test_add_iteration_stores_required_fields():
    manager = _manager()
    session = manager.start_session("Analizza i ticket", "csv", {"rows": 10})

    iteration = manager.add_iteration(
        session["session_id"],
        "Analizza i ticket",
        _payload(),
    )

    assert iteration["iteration_number"] == 1
    assert iteration["request_type"] == "initial_analysis"
    assert iteration["analysis_plan"]["analysis_type"] == "count_occurrences"
    assert iteration["deterministic_results"]["counts"][0]["count"] == 3
    assert iteration["insights"]["key_findings"]
    assert iteration["final_report_snapshot"].startswith("# Report")


def test_iteration_number_increments():
    manager = _manager()
    session = manager.start_session("Analizza i ticket", "csv", {})

    first = manager.add_iteration(session["session_id"], "Analizza i ticket", _payload())
    second = manager.add_iteration(
        session["session_id"],
        "Approfondisci il risultato",
        _payload("top_n"),
    )

    assert first["iteration_number"] == 1
    assert second["iteration_number"] == 2
    assert manager.get_session(session["session_id"])["iteration_count"] == 2


def test_get_session_returns_defensive_copy():
    manager = _manager()
    session = manager.start_session("Analizza i ticket", "csv", {})
    manager.add_iteration(session["session_id"], "Analizza i ticket", _payload())

    recovered = manager.get_session(session["session_id"])
    recovered["iterations"][0]["user_prompt"] = "modificato esternamente"

    assert manager.get_session(session["session_id"])["iterations"][0]["user_prompt"] == (
        "Analizza i ticket"
    )


def test_build_context_for_next_iteration_uses_latest_results():
    manager = _manager()
    session = manager.start_session(
        "Analizza i ticket",
        "excel",
        {"rows": 10, "columns": ["stato"]},
    )
    manager.add_iteration(session["session_id"], "Analizza i ticket", _payload())
    manager.add_iteration(
        session["session_id"],
        "Segmenta per stato",
        _payload("top_n"),
    )

    context = manager.build_context_for_next_iteration(session["session_id"])

    assert context["original_user_request"] == "Analizza i ticket"
    assert context["iteration_count"] == 2
    assert context["latest_iteration"]["request_type"] == "segmentation_request"
    assert context["latest_analysis_plan"]["analysis_type"] == "top_n"
    assert len(context["request_history"]) == 2


def test_export_session_summary_contains_counts_and_latest_report():
    manager = _manager()
    session = manager.start_session("Analizza i ticket", "oracle", {"rows": 10})
    manager.add_iteration(session["session_id"], "Analizza i ticket", _payload())
    manager.add_iteration(
        session["session_id"],
        "Mostra solo valori oltre 100",
        _payload("numeric_aggregation"),
    )

    summary = manager.export_session_summary(session["session_id"])

    assert summary["iteration_count"] == 2
    assert summary["request_type_counts"]["initial_analysis"] == 1
    assert summary["request_type_counts"]["threshold_comparison"] == 1
    assert summary["analysis_types"] == ["count_occurrences", "numeric_aggregation"]
    assert summary["latest_final_report"].startswith("# Report")
    json.dumps(summary)


def test_missing_session_id_is_handled_explicitly():
    manager = _manager()

    assert manager.get_session("missing") is None
    with pytest.raises(KeyError):
        manager.add_iteration("missing", "prompt", {})
    with pytest.raises(KeyError):
        manager.build_context_for_next_iteration("missing")
    with pytest.raises(KeyError):
        manager.export_session_summary("missing")


def test_local_request_classification_covers_supported_types():
    prompts = {
        "Analizza il dataset": "initial_analysis",
        "Approfondisci i KPI principali": "refinement",
        "Segmenta i ticket per stato": "segmentation_request",
        "Considera solo l'ultimo mese": "time_window_request",
        "Confronta importi superiori a 100": "threshold_comparison",
        "Approfondisci le anomalie e gli outlier": "anomaly_deep_dive",
    }

    for index, (prompt, expected_type) in enumerate(prompts.items(), start=1):
        manager = AnalysisSessionManager(id_factory=lambda index=index: f"session-{index}")
        session = manager.start_session("Analizza il dataset", "csv", {})
        iteration = manager.add_iteration(session["session_id"], prompt, _payload())
        assert iteration["request_type"] == expected_type
