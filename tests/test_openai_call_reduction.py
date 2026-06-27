import pandas as pd

from agents.data_extractor import DataExtractorAgent
from agents.data_validator import DataValidatorAgent
from coordinator import Coordinator
import services.llm_gateway as llm_gateway_module
from services.analysis_service import try_run_followup_analysis
from utils.context import AgentContext


class _CountingGateway:
    def __init__(self):
        self.client = object()
        self.model = "gpt-5.5"
        self.calls = 0
        self.max_calls = 2

    def complete(self, messages, task_name, temperature=None, cache_key=None, fallback=None):
        self.calls += 1
        return {
            "status": "completed",
            "content": f"arricchimento {task_name}",
            "model": self.model,
            "task_name": task_name,
            "cached": False,
            "error": None,
            "usage": {
                "calls": self.calls,
                "prompt_tokens": None,
                "completion_tokens": None,
                "total_tokens": None,
            },
        }

    def get_usage_summary(self):
        return {
            "model": self.model,
            "calls_used": self.calls,
            "max_calls": self.max_calls,
            "cache_enabled": True,
            "cache_size": 0,
        }

    def reset_usage(self):
        self.calls = 0


def test_data_extractor_does_not_call_openai_for_loaded_csv(monkeypatch):
    calls = {"openai": 0}
    agent = DataExtractorAgent()
    monkeypatch.setattr(agent, "call_openai", lambda *args, **kwargs: calls.__setitem__("openai", calls["openai"] + 1))
    context = AgentContext(
        user_input="analizza i ticket",
        raw_data={
            "dataframe": pd.DataFrame({"stato": ["open"]}),
            "extraction_suggestion": {"description": "locale"},
        },
        metadata={"source_type": "csv"},
    )

    result = agent.process(context)

    assert calls["openai"] == 0
    assert result.raw_data["extraction_plan"]["mode"] == "local"


def test_data_validator_does_not_call_openai(monkeypatch):
    calls = {"openai": 0}
    agent = DataValidatorAgent()
    monkeypatch.setattr(agent, "call_openai", lambda *args, **kwargs: calls.__setitem__("openai", calls["openai"] + 1))
    context = AgentContext(
        user_input="analizza i ticket",
        raw_data={"dataframe": pd.DataFrame({"stato": ["open", "closed"]})},
    )

    result = agent.process(context)

    assert calls["openai"] == 0
    assert result.is_valid is True
    assert result.validation_results["validation_report"]["mode"] == "local"


def test_followup_filter_reruns_local_analysis_without_openai():
    context = AgentContext(
        user_input="analizza consegna",
        raw_data={
            "dataframe": pd.DataFrame({
                "METODOCONSEGNA": ["CONSEGNA_A_MANO", "POSTA", "CONSEGNA_A_MANO"],
                "DATASOTTOSCRIZIONE": ["2026-01-01", "2026-01-02", "2026-01-03"],
                "CREAZIONE_ANTENNA": ["2026-01-03", "2026-01-04", "2026-01-07"],
            })
        },
    )

    result = try_run_followup_analysis(
        "mi fai l'analisi per i soli record che hanno il metodo di consegna definito come consegna a mano?",
        context,
    )

    assert result is not None
    assert result["followup_execution_type"] == "filtered_reanalysis"
    assert result["context"].filtered_row_count == 2


def test_full_csv_pipeline_does_not_exceed_two_openai_calls(monkeypatch, tmp_path):
    gateway = _CountingGateway()
    monkeypatch.setattr(llm_gateway_module, "_DEFAULT_GATEWAY", gateway)
    monkeypatch.chdir(tmp_path)

    context = Coordinator().run(
        "analizza ticket per stato",
        metadata={
            "source_type": "csv",
            "dataframe": pd.DataFrame({
                "stato": ["open", "closed", "open"],
                "created_at": pd.date_range("2026-01-01", periods=3),
            }),
        },
    )

    assert context.is_valid is True
    assert gateway.calls <= 2
