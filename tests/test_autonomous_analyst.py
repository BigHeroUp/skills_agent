import json

import pandas as pd

import agents.data_processor as data_processor_module
from agents.data_processor import DataProcessorAgent
from services.autonomous_analyst import AutonomousAnalyst
from utils.analysis_history_manager import AnalysisHistoryManager
from utils.context import AgentContext


def _ticket_dataframe():
    return pd.DataFrame({
        "stato": ["open", "closed", "open", "pending", "closed", "closed"],
        "categoria": ["A", "A", "B", "B", "B", "B"],
        "created_at": [
            "2026-01-01",
            "2026-01-01",
            "2026-01-02",
            "2026-01-03",
            "2026-01-03",
            "2026-01-03",
        ],
        "resolved_at": [
            "2026-01-03",
            "2026-01-02",
            "2026-01-04",
            "2026-01-04",
            "2026-01-05",
            "2026-01-05",
        ],
        "priority_score": [1, 2, 3, 2, 4, 4],
        "owner": ["Mario", "Mario", "Luca", None, "Luca", "Luca"],
    })


def test_autonomous_plan_generation_on_ticket_like_dataframe():
    analyst = AutonomousAnalyst()
    plan = analyst.build_plan("analizza i ticket", _ticket_dataframe())

    step_ids = [step.step_id for step in plan.steps]
    assert "category-distribution" in step_ids
    assert "time-trend" in step_ids
    assert "duration-summary" in step_ids
    assert "null-detection" in step_ids
    assert "duplicate-detection" in step_ids


def test_autonomous_multi_step_execution_is_json_serializable():
    analyst = AutonomousAnalyst()
    payload = analyst.run("fammi un'analisi completa", _ticket_dataframe())

    assert len(payload["autonomous_analysis_results"]) >= 5
    assert payload["autonomous_executive_summary"]
    assert payload["autonomous_recommendations"]
    json.dumps(payload)


def test_autonomous_results_include_null_duplicate_and_time_trend():
    analyst = AutonomousAnalyst()
    payload = analyst.run("analizza i ticket", _ticket_dataframe())
    results_by_id = {
        result["step_id"]: result
        for result in payload["autonomous_analysis_results"]
    }

    assert results_by_id["null-detection"]["result"]["total_nulls"] >= 1
    assert results_by_id["duplicate-detection"]["result"]["duplicate_rows"] >= 1
    assert results_by_id["time-trend"]["result"]["points"]


def test_specific_request_stays_single_plan():
    analyst = AutonomousAnalyst()

    assert analyst.should_run_autonomous("conta ticket per stato") is False
    assert analyst.should_run_autonomous("analizza i ticket") is True


def test_data_processor_enriches_context_in_autonomous_mode(monkeypatch, tmp_path):
    manager = AnalysisHistoryManager(db_path=tmp_path / "analysis_history.db")
    monkeypatch.setattr(data_processor_module, "AnalysisHistoryManager", lambda: manager)

    calls = {"openai": 0}
    agent = DataProcessorAgent.__new__(DataProcessorAgent)
    agent.name = "DataProcessor"
    agent.log = lambda message: None
    agent.build_prompt_with_skill = lambda prompt: prompt

    def fake_call_openai(messages):
        calls["openai"] += 1
        return "report deterministico"

    agent.call_openai = fake_call_openai
    context = AgentContext(
        user_input="analizza i ticket",
        raw_data={"dataframe": _ticket_dataframe()},
        metadata={"source_type": "csv"},
    )

    result = agent.process(context)

    assert result.autonomous_mode is True
    assert result.autonomous_analysis_plan["steps"]
    assert result.autonomous_analysis_results
    assert result.autonomous_executive_summary
    assert result.autonomous_recommendations
    assert result.processed_data["autonomous_mode"] is True
    assert calls["openai"] == 0
