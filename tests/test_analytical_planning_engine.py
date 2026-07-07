import pandas as pd

import agents.data_processor as data_processor_module
from agents.analyst import AnalystAgent
from agents.data_processor import DataProcessorAgent
from agents.report_generator import ReportGeneratorAgent
from services.analysis_service import try_run_followup_analysis
from services.analytical_planning_engine import AnalyticalPlanningEngine, VisualizationPlanner
from services.semantic_column_classifier import SemanticColumnClassifier
from services.semantic_feature_engineering import SemanticFeatureEngineeringEngine
from services.senior_data_analyst_engine import SeniorDataAnalystEngine
from utils.analysis_history_manager import AnalysisHistoryManager
from utils.chart_generator import ChartGenerator
from utils.context import AgentContext


REQUEST = (
    "Le date di data sottoscrizione sono in GMT: aggiungi +1h a data sottoscrizione "
    "e post aggiornamento analizza la distribuzione dei tempi di attivazione da data "
    "sottoscrizione a creazione antenna, capisci se i tempi lunghissimi sono "
    "riconducibili a giornate specifiche o a varianza."
)


def _df_with_gmt_shift_and_negatives():
    rows = []
    durations = [2, 3, 4, 40, 42, 41, 2, 3, 4, 5, 7, 8, -1, -2, -3, 2, 3, 4, 5, 6]
    for index, duration in enumerate(durations):
        if index in {3, 4, 5}:
            start = pd.Timestamp("2026-01-04 23:30:00")
        else:
            start = pd.Timestamp("2026-01-01 10:00:00") + pd.Timedelta(days=index)
        end = start + pd.Timedelta(days=duration)
        rows.append({
            "DATASOTTOSCRIZIONE": start.strftime("%Y-%m-%d %H:%M:%S"),
            "CREAZIONE_ANTENNA": end.strftime("%Y-%m-%d %H:%M:%S"),
            "METODOCONSEGNA": "CONSEGNA_A_MANO" if index % 2 == 0 else "DOMICILIO",
            "CANALETECNICO": "WEB" if index % 3 else "BACKOFFICE",
            "PYID": f"PY-{index:04d}",
            "CONTRATTOID": f"C-{index:04d}",
        })
    return pd.DataFrame(rows)


def _run_pipeline(df, monkeypatch, tmp_path):
    manager = AnalysisHistoryManager(db_path=tmp_path / "analysis_history.db")
    monkeypatch.setattr(data_processor_module, "AnalysisHistoryManager", lambda: manager)
    context = AgentContext(
        user_input=REQUEST,
        raw_data={"dataframe": df.copy()},
        metadata={"source_type": "excel"},
    )
    for agent in (DataProcessorAgent(), AnalystAgent(), ReportGeneratorAgent()):
        context = agent.process(context)
    return context


def test_planner_recognizes_gmt_plus_one_hour_without_overwriting_source():
    df = _df_with_gmt_shift_and_negatives()
    engine = AnalyticalPlanningEngine()
    plan = engine.build_execution_plan(REQUEST, df)
    transformation = plan["transformations"][0]

    assert plan["intent"]["requested_transformations"][0]["amount"] == 1
    assert transformation["type"] == "datetime_shift"
    assert transformation["source_column"] == "DATASOTTOSCRIZIONE"
    assert transformation["output_column"] == "DATASOTTOSCRIZIONE_ADJUSTED"
    assert transformation["unit"] == "hour"
    assert transformation["status"] == "planned"

    transformed, payload = engine.transformation_executor.execute(df, plan)

    assert "DATASOTTOSCRIZIONE_ADJUSTED" in transformed.columns
    assert transformed["DATASOTTOSCRIZIONE"].equals(df["DATASOTTOSCRIZIONE"])
    assert transformed["DATASOTTOSCRIZIONE_ADJUSTED"].iloc[0] == pd.Timestamp("2026-01-01 11:00:00")
    assert payload["transformation_results"][0]["parsed_count"] == len(df)
    assert payload["transformation_results"][0]["failed_parse_count"] == 0
    assert payload["transformation_results"][0]["min_after"] is not None
    assert payload["transformation_results"][0]["max_after"] is not None


def test_semantic_feature_engineering_uses_adjusted_start_column():
    df = _df_with_gmt_shift_and_negatives()
    engine = AnalyticalPlanningEngine()
    execution_plan = engine.build_execution_plan(REQUEST, df)
    transformed, _ = engine.transformation_executor.execute(df, execution_plan)
    semantic_columns = SemanticColumnClassifier().classify_dataframe(transformed)

    feature_plan = SemanticFeatureEngineeringEngine().build_feature_plan(
        REQUEST,
        transformed,
        semantic_columns,
        {},
        execution_plan,
    )

    sources = feature_plan["features"][0]["source_columns"]
    assert sources["start"] == "DATASOTTOSCRIZIONE_ADJUSTED"
    assert sources["end"] == "CREAZIONE_ANTENNA"


def test_pipeline_excludes_negative_durations_from_primary_kpi(monkeypatch, tmp_path):
    context = _run_pipeline(_df_with_gmt_shift_and_negatives(), monkeypatch, tmp_path)
    df = context.raw_data["dataframe"]
    metric = "TEMPO_ATTIVAZIONE_GIORNI"

    assert context.is_valid is True
    assert "DATASOTTOSCRIZIONE_ADJUSTED" in df.columns
    assert metric in df.columns
    assert pd.to_numeric(df[metric], errors="coerce").dropna().min() >= 0
    assert context.metric_filtering_policy["exclude_negative_from_primary_kpi"] is True
    assert context.metric_filtering_policy["negative_values_treatment"] == "data_quality_issue"
    assert context.quality_gate_results[0]["status"] == "requires_user_decision"
    assert context.data_quality_issues[0]["negative_duration_count"] == 3
    assert context.semantic_feature_results["features"][0]["source_columns"]["start"] == "DATASOTTOSCRIZIONE_ADJUSTED"
    assert context.analytical_intent_plan["time_axis"] == "DATASOTTOSCRIZIONE_ADJUSTED"


def test_activation_report_is_business_first_and_hides_raw_technical_details(monkeypatch, tmp_path):
    context = _run_pipeline(_df_with_gmt_shift_and_negatives(), monkeypatch, tmp_path)
    report = context.final_report

    assert report.startswith("# Report business")
    assert "## Risposta breve" in report
    assert "## Numeri chiave" in report
    assert "## Qualita dato" in report
    assert "## Visualizzazioni consigliate" in report
    assert "method_details" not in report
    assert "row_index" not in report
    assert "{'" not in report
    assert "Integrare media, mediana" not in report


def test_visualization_plan_and_dashboard_charts_are_limited_to_four(monkeypatch, tmp_path):
    context = _run_pipeline(_df_with_gmt_shift_and_negatives(), monkeypatch, tmp_path)
    planned = context.visualization_plan
    payload = ChartGenerator.generate_dashboard_charts(context.raw_data["dataframe"], context.insights)

    assert len(VisualizationPlanner().build(context.analytical_execution_plan["intent"])) == 4
    assert len(planned) == 4
    assert len(payload["charts"]) <= 4
    assert planned[-1]["x"] == "DATASOTTOSCRIZIONE_ADJUSTED"


def test_followup_filtered_analysis_compares_baseline_vs_subset(monkeypatch, tmp_path):
    context = _run_pipeline(_df_with_gmt_shift_and_negatives(), monkeypatch, tmp_path)
    result = try_run_followup_analysis(
        "mi fai la stessa analisi usando solo record con metodo consegna consegna a mano?",
        context,
    )

    assert result["message"].startswith("Confronto con analisi precedente")
    assert result["followup_execution_type"] == "filtered_reanalysis"
    assert result["context"].followup_comparison_results["baseline_rows"] == len(context.raw_data["dataframe"])
    assert result["context"].followup_comparison_results["subset_rows"] == result["filtered_row_count"]
    assert result["context"].followup_comparison_results["metric"] == "TEMPO_ATTIVAZIONE_GIORNI"
    assert result["context"].processed_data["followup_comparison_results"]["conclusion"] in {
        "subset_worse",
        "subset_better",
        "subset_similar",
    }
