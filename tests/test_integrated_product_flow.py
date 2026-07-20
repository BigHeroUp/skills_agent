from datetime import datetime

import pandas as pd

from agents.knowledge_graph_agent import KnowledgeGraphAgent
from agents.product_intelligence_agent import ProductIntelligenceAgent
from coordinator import Coordinator
from services.analysis_service import format_product_intelligence_summary
from services.integrated_product_flow import IntegratedProductFlow
from services.knowledge_graph.store import KnowledgeGraphStore
from services.narrative import NarrativePolicy, OptionalNarrativeService
from utils.context import AgentContext


class FakeGateway:
    def __init__(self):
        self.calls = 0

    def complete(self, messages, **kwargs):
        self.calls += 1
        return {
            "status": "completed",
            "content": "Executive narrative based only on deterministic facts.",
            "model": "fake-model",
            "error": None,
        }


def _context():
    context = AgentContext(
        user_input="Analyze response time",
        raw_data={
            "dataframe": pd.DataFrame({
                "created_at": pd.to_datetime(["2026-01-01", "2026-01-02"]),
                "response_time": [10.0, 20.0],
            }),
        },
        metadata={"source_type": "csv", "language": "en"},
        created_at=datetime(2026, 1, 3, 10, 0, 0),
    )
    context.primary_metric = "response_time"
    context.time_axis = "created_at"
    context.confidence_score = 0.8
    context.final_report = "Deterministic report: response time increased."
    context.recommended_analytical_steps = [{
        "step": "Segment response time by service",
        "reason": "Verify whether the change is concentrated.",
        "priority": "high",
        "source": "strategy",
        "confidence": 0.8,
    }]
    return context


def test_integrated_flow_connects_every_post_analysis_layer(tmp_path):
    context = _context()
    graph_path = tmp_path / "knowledge_graph.json"
    KnowledgeGraphAgent(KnowledgeGraphStore(graph_path)).process(context)
    original_report = context.final_report
    flow = IntegratedProductFlow(
        kg_path=graph_path,
        experience_path=tmp_path / "experience.json",
    )

    result = flow.run(context)

    assert result["status"] == "completed"
    assert result["knowledge_graph"]["validation"]["status"] in {"valid", "degraded"}
    assert result["consistency"]["status"] == "consistent"
    assert result["experience"]["refresh"]["status"] == "ok"
    assert result["recommendation"]["status"] == "ok"
    assert result["decision"]["status"] == "selected"
    assert result["decision"]["selected"]["action"] == "Segment response time by service"
    assert result["narrative"]["status"] == "disabled"
    assert context.final_report == original_report


def test_product_agent_publishes_one_payload_into_context(tmp_path):
    context = _context()
    graph_path = tmp_path / "knowledge_graph.json"
    KnowledgeGraphAgent(KnowledgeGraphStore(graph_path)).process(context)
    flow = IntegratedProductFlow(
        kg_path=graph_path,
        experience_path=tmp_path / "experience.json",
    )

    result = ProductIntelligenceAgent(flow).process(context)

    assert result.product_intelligence["execution_type"] == "integrated_product_intelligence"
    assert result.processed_data["product_intelligence"] == result.product_intelligence


def test_narrative_is_opt_in_and_never_replaces_final_report(tmp_path):
    context = _context()
    context.metadata["enable_narrative"] = True
    graph_path = tmp_path / "knowledge_graph.json"
    KnowledgeGraphAgent(KnowledgeGraphStore(graph_path)).process(context)
    gateway = FakeGateway()
    narrative = OptionalNarrativeService(gateway, NarrativePolicy(enabled=True))
    flow = IntegratedProductFlow(
        kg_path=graph_path,
        experience_path=tmp_path / "experience.json",
        narrative_service=narrative,
    )

    result = flow.run(context)

    assert result["narrative"]["used_llm"] is True
    assert result["narrative"]["content"].startswith("Executive narrative")
    assert context.final_report == "Deterministic report: response time increased."
    assert gateway.calls == 1


def test_product_agent_is_non_blocking_on_integration_failure():
    class BrokenFlow:
        def run(self, context):
            raise RuntimeError("integration unavailable")

    context = _context()
    original_validity = context.is_valid

    result = ProductIntelligenceAgent(BrokenFlow()).process(context)

    assert result.product_intelligence["status"] == "error"
    assert result.is_valid is original_validity
    assert result.errors == []


def test_product_flow_can_be_disabled_per_analysis():
    context = _context()
    context.metadata["integrated_product_flow"] = False

    result = ProductIntelligenceAgent().process(context)

    assert result.product_intelligence["status"] == "disabled"


def test_dashboard_summary_exposes_selected_action_without_replacing_report(tmp_path):
    context = _context()
    graph_path = tmp_path / "knowledge_graph.json"
    KnowledgeGraphAgent(KnowledgeGraphStore(graph_path)).process(context)
    context.product_intelligence = IntegratedProductFlow(
        kg_path=graph_path,
        experience_path=tmp_path / "experience.json",
    ).run(context)

    summary = format_product_intelligence_summary(context)

    assert "## Product Intelligence" in summary
    assert "Next best action: Segment response time by service" in summary
    assert "Knowledge consistency: consistent" in summary


def test_coordinator_runs_the_integrated_product_flow_end_to_end(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    context = Coordinator().run(
        "Analyze response time by date",
        metadata={
            "source_type": "csv",
            "dataframe": pd.DataFrame({
                "created_at": pd.date_range("2026-01-01", periods=4),
                "response_time": [10.0, 12.0, 18.0, 20.0],
            }),
        },
    )

    assert context.product_intelligence["execution_type"] == "integrated_product_intelligence"
    assert context.product_intelligence["status"] in {
        "completed",
        "completed_without_decision",
    }
    assert "validation" in context.product_intelligence["knowledge_graph"]
    assert "recommendation" in context.product_intelligence
    assert "decision" in context.product_intelligence
    assert "narrative" in context.product_intelligence
