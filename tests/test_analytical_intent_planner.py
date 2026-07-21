import pandas as pd

from agents.analyst import AnalystAgent
from agents.data_processor import DataProcessorAgent
from agents.report_generator import ReportGeneratorAgent
from services.analysis_service import try_run_followup_analysis
from services.analytical_intent_planner import AnalyticalIntentPlanner
from services.semantic_column_classifier import SemanticColumnClassifier
from services.semantic_feature_engineering import SemanticFeatureEngineeringEngine
from utils.context import AgentContext


REQUEST = (
    "analisi sulla distribuzione dei tempi di attivazione usando data sottoscrizione "
    "e creazione antenna e capire se i tempi lunghissimi sono riconducibili a giornate specifiche"
)


def _activation_df():
    rows = []
    for index in range(20):
        start_day = pd.Timestamp("2026-01-01") + pd.Timedelta(days=index // 2)
        duration = 2 + (index % 3)
        if index in {6, 7, 8, 9}:
            start_day = pd.Timestamp("2026-01-04")
            duration = 40
        rows.append({
            "DATASOTTOSCRIZIONE": start_day.strftime("%Y-%m-%d"),
            "CREAZIONE_ANTENNA": (start_day + pd.Timedelta(days=duration)).strftime("%Y-%m-%d"),
            "METODOCONSEGNA": "CONSEGNA_A_MANO" if index % 2 == 0 else "DOMICILIO",
            "IDCONTRATTOTLM": f"C-{index:04d}",
            "PYID": f"PY-{index:04d}",
            "CONTRATTOID": 10000 + index,
            "SERIALNUMBER": f"SN-{index:04d}",
        })
    return pd.DataFrame(rows)


def _run_local_pipeline(df):
    context = AgentContext(
        user_input=REQUEST,
        raw_data={"dataframe": df},
        metadata={"source_type": "excel"},
    )
    for agent in (DataProcessorAgent(), AnalystAgent(), ReportGeneratorAgent()):
        context = agent.process(context)
    return context


def test_intent_planner_selects_activation_metric_axes_segments_and_forbidden_columns():
    df = _activation_df()
    feature_engine = SemanticFeatureEngineeringEngine()
    semantic_columns = SemanticColumnClassifier().classify_dataframe(df)
    plan = feature_engine.build_feature_plan(REQUEST, df, semantic_columns)
    enriched, feature_results = feature_engine.apply_feature_plan(df, plan)
    semantic_columns = SemanticColumnClassifier().classify_dataframe(enriched)

    intent = AnalyticalIntentPlanner().build_plan(
        REQUEST,
        enriched,
        feature_results,
        semantic_columns,
        {},
    )

    assert intent["primary_metric"] == "TEMPO_ATTIVAZIONE_GIORNI"
    assert intent["time_axis"] == "DATASOTTOSCRIZIONE"
    assert intent["event_axis"] == "CREAZIONE_ANTENNA"
    assert "METODOCONSEGNA" in intent["segmentations"]
    assert {"PYID", "CONTRATTOID", "IDCONTRATTOTLM"}.issubset(set(intent["forbidden_columns"]))
    assert intent["temporal_concentration"] is True


def test_temporal_concentration_detects_concentrated_and_distributed_outliers():
    planner = AnalyticalIntentPlanner()
    concentrated = pd.DataFrame({
        "DATASOTTOSCRIZIONE": ["2026-01-01"] * 4 + [f"2026-01-{day:02d}" for day in range(2, 18)],
        "TEMPO_ATTIVAZIONE_GIORNI": [40, 42, 41, 43] + [2, 3, 2, 4, 3, 2, 3, 2, 4, 3, 2, 3, 2, 4, 3, 2],
    })
    distributed = pd.DataFrame({
        "DATASOTTOSCRIZIONE": [f"2026-02-{day:02d}" for day in range(1, 21)],
        "TEMPO_ATTIVAZIONE_GIORNI": [40, 2, 3, 42, 2, 3, 41, 2, 3, 43, 2, 3, 2, 3, 2, 4, 3, 2, 4, 3],
    })

    concentrated_result = planner.temporal_concentration(
        concentrated,
        "TEMPO_ATTIVAZIONE_GIORNI",
        "DATASOTTOSCRIZIONE",
    )
    distributed_result = planner.temporal_concentration(
        distributed,
        "TEMPO_ATTIVAZIONE_GIORNI",
        "DATASOTTOSCRIZIONE",
    )

    assert concentrated_result["conclusion"] == "concentrated"
    assert concentrated_result["top_days"][0]["day"] == "2026-01-01"
    assert distributed_result["conclusion"] == "distributed"


def test_e2e_report_uses_intent_plan_and_excludes_technical_id_analysis():
    context = _run_local_pipeline(_activation_df())
    report = context.final_report

    assert context.is_valid is True
    assert context.analytical_intent_plan["primary_metric"] == "TEMPO_ATTIVAZIONE_GIORNI"
    assert context.analytical_intent_plan["time_axis"] == "DATASOTTOSCRIZIONE"
    assert context.temporal_concentration_results["status"] == "computed"
    assert "top PYID" not in report
    assert "top CONTRATTOID" not in report
    assert "top SERIALNUMBER" not in report
    assert "IDCONTRATTOTLM / TEMPO_ATTIVAZIONE_GIORNI" not in report
    assert "Correlazione Pearson piu alta: IDCONTRATTOTLM" not in report
    assert "CREAZIONE_ANTENNA è crescente" not in report
    assert "Concentrazione temporale dei tempi lunghi" in report


def test_followup_delivery_filter_reruns_pipeline_on_filtered_dataframe():
    context = _run_local_pipeline(_activation_df())
    result = try_run_followup_analysis(
        "mi fai l'analisi per i soli record che hanno il metodo di consegna definito come consegna a mano?",
        context,
    )
    new_context = result["context"]

    assert result["followup_execution_type"] == "filtered_reanalysis"
    assert result["applied_filters"][0]["column"] == "METODOCONSEGNA"
    assert result["applied_filters"][0]["value"] == "CONSEGNA_A_MANO"
    assert result["filtered_row_count"] == len(new_context.raw_data["dataframe"])
    assert set(new_context.raw_data["dataframe"]["METODOCONSEGNA"]) == {"CONSEGNA_A_MANO"}
    assert new_context.followup_execution_type == "filtered_reanalysis"
    assert new_context.processed_data["filtered_row_count"] == result["filtered_row_count"]
    assert "TEMPO_ATTIVAZIONE_GIORNI" in new_context.raw_data["dataframe"].columns


def test_categorical_contract_count_pipeline_keeps_real_dataframe_and_report():
    df = pd.DataFrame({
        "CONTRATTOID": range(1, 7),
        "STATO_CONTRATTO": ["ATTIVO", "ATTIVO", "NON_ATTIVO", "ATTIVO", "NON_ATTIVO", "ATTIVO"],
        "STATO_ANTENNA": ["ATTIVA", "ASSENTE", "ATTIVA", "ATTIVA", "ASSENTE", "ATTIVA"],
        "AGG_ANTENNA": ["A1", None, "A2", "A3", None, "A4"],
    })
    context = AgentContext(
        user_input="Dimmi il numero totale di contratti attivi, quelli non attivi e le relative antenne",
        raw_data={"dataframe": df},
        metadata={"source_type": "excel"},
    )

    for agent in (DataProcessorAgent(), AnalystAgent(), ReportGeneratorAgent()):
        context = agent.process(context)

    assert not any("Colonna non disponibile" in error for error in context.errors)
    assert context.execution_summary["row_count"] == 6
    assert context.deterministic_results["target_column"] == "STATO_CONTRATTO"
    assert context.deterministic_results["total_records"] == 6
    assert "6 record" in context.final_report
    assert "0 record" not in context.final_report
