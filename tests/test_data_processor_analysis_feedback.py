import pandas as pd

import agents.data_processor as data_processor_module
from agents.data_processor import DataProcessorAgent
from utils.analysis_history_manager import AnalysisHistoryManager
from utils.context import AgentContext


def test_data_processor_enriches_context_with_analysis_pattern_metadata(monkeypatch, tmp_path):
    manager = AnalysisHistoryManager(db_path=tmp_path / "analysis_history.db")
    monkeypatch.setattr(data_processor_module, "AnalysisHistoryManager", lambda: manager)

    agent = DataProcessorAgent.__new__(DataProcessorAgent)
    agent.name = "DataProcessor"
    agent.log = lambda message: None
    agent.build_prompt_with_skill = lambda prompt: prompt
    agent.call_openai = lambda messages: "report deterministico"

    context = AgentContext(
        user_input="conta ticket per stato",
        raw_data={"dataframe": pd.DataFrame({"stato": ["open", "closed", "open"]})},
        metadata={"source_type": "csv"},
    )

    result = agent.process(context)

    assert result.analysis_pattern_id is not None
    assert result.plan_source == "new"
    assert result.confidence_score == 0.0
    assert result.similarity_score is None
    assert result.similarity_method is None
    assert result.processed_data["analysis_pattern_id"] == result.analysis_pattern_id
    assert result.processed_data["confidence_score"] == 0.0
    assert result.processed_data["similarity_method"] is None
    assert result.execution_summary["analysis_pattern_id"] == result.analysis_pattern_id
    assert result.analysis_plan["knowledge_enrichment"]["patterns"]
    assert result.detected_patterns
    assert result.knowledge_analysis_steps
    assert result.processed_data["detected_patterns"] == result.detected_patterns
