import json

import pandas as pd

import agents.data_processor as data_processor_module
from agents.data_processor import DataProcessorAgent
from services.domain_pack_loader import DomainPackLoader
from utils.analysis_history_manager import AnalysisHistoryManager
from utils.context import AgentContext


def test_lists_available_domain_packs():
    packs = DomainPackLoader().list_available_packs()

    assert any(pack["pack_id"] == "telepedaggio" for pack in packs)
    telepedaggio = next(pack for pack in packs if pack["pack_id"] == "telepedaggio")
    assert telepedaggio["valid"] is True


def test_loads_telepedaggio_pack():
    pack = DomainPackLoader().load_pack("telepedaggio")

    assert pack["pack_id"] == "telepedaggio"
    assert pack["manifest"]["name"] == "Telepedaggio"
    assert any(
        pattern["pattern_id"] == "activation_time_analysis"
        for pattern in pack["patterns"]
    )
    assert "Report telepedaggio" in pack["report_template"]


def test_validates_required_files(tmp_path):
    pack_dir = tmp_path / "incomplete"
    pack_dir.mkdir()
    (pack_dir / "domain_pack.yaml").write_text("pack_id: incomplete\n", encoding="utf-8")

    validation = DomainPackLoader(tmp_path).validate_pack("incomplete")

    assert validation["valid"] is False
    assert "patterns.json" in validation["missing_files"]
    assert validation["errors"]


def test_suggest_pack_with_telepedaggio_request():
    suggestion = DomainPackLoader().suggest_pack(
        "Analizza tempi di attivazione telepedaggio per contratto e SLA"
    )

    assert suggestion is not None
    assert suggestion["pack_id"] == "telepedaggio"
    assert suggestion["confidence_score"] > 0
    assert "attivazione" in suggestion["matched_terms"]


def test_suggest_pack_with_compatible_metadata():
    suggestion = DomainPackLoader().suggest_pack(
        "Analizza il dataset",
        {
            "columns": [
                "id_contratto",
                "data_sottoscrizione",
                "data_attivazione",
                "stato_antenna",
                "metodo_consegna",
            ]
        },
    )

    assert suggestion is not None
    assert suggestion["pack_id"] == "telepedaggio"
    assert "sottoscrizione" in suggestion["metadata_signals"]


def test_export_pack_knowledge_is_json_serializable():
    knowledge = DomainPackLoader().export_pack_knowledge("telepedaggio")

    encoded = json.dumps(knowledge, ensure_ascii=False)
    assert "telepedaggio" in encoded


def test_missing_pack_returns_validation_error_and_no_suggestion():
    loader = DomainPackLoader()

    validation = loader.validate_pack("missing-pack")

    assert validation["valid"] is False
    assert loader.suggest_pack("richiesta completamente generica") is None


def test_data_processor_stores_domain_pack_context(monkeypatch, tmp_path):
    manager = AnalysisHistoryManager(db_path=tmp_path / "analysis_history.db")
    monkeypatch.setattr(data_processor_module, "AnalysisHistoryManager", lambda: manager)

    agent = DataProcessorAgent.__new__(DataProcessorAgent)
    agent.name = "DataProcessor"
    agent.log = lambda message: None
    agent.build_prompt_with_skill = lambda prompt: prompt
    agent.call_openai = lambda messages: "report deterministico"

    context = AgentContext(
        user_input="Analizza tempi attivazione telepedaggio e SLA per metodo consegna",
        raw_data={
            "dataframe": pd.DataFrame({
                "id_contratto": [1, 2, 3],
                "data_sottoscrizione": pd.to_datetime([
                    "2026-01-01",
                    "2026-01-02",
                    "2026-01-05",
                ]),
                "data_attivazione": pd.to_datetime([
                    "2026-01-03",
                    "2026-01-08",
                    "2026-01-09",
                ]),
                "metodo_consegna": ["corriere", "agenzia", "consegna a mano"],
                "stato_antenna": ["attiva", "spenta", "non presente"],
            })
        },
        metadata={"source_type": "csv"},
    )

    result = agent.process(context)

    assert result.domain_pack_context["status"] == "detected"
    assert result.domain_pack_context["pack_id"] == "telepedaggio"
    assert result.processed_data["domain_pack_context"] == result.domain_pack_context
    assert (
        result.analysis_plan["knowledge_enrichment"]["domain_pack"]["pack_id"]
        == "telepedaggio"
    )
    assert result.analytical_strategy["domain_strategy_rules"]
