import pandas as pd

import agents.data_processor as data_processor_module
from agents.analyst import AnalystAgent
from agents.data_processor import DataProcessorAgent
from agents.report_generator import ReportGeneratorAgent
from services.business_insight_generator import BusinessInsightGenerator
from services.semantic_column_classifier import SemanticColumnClassifier
from services.semantic_feature_engineering import SemanticFeatureEngineeringEngine
from services.senior_data_analyst_engine import SeniorDataAnalystEngine
from utils.analysis_history_manager import AnalysisHistoryManager
from utils.chart_generator import ChartGenerator
from utils.context import AgentContext
from utils.pdf_generator import PDFGenerator


REQUEST = (
    "analisi sulla distribuzione dei tempi di attivazione utilizzando data "
    "sottoscrizione e creazione antenna e capire se i tempi lunghissimi sono "
    "riconducibili a giornate specifiche"
)


def _activation_df():
    return pd.DataFrame({
        "DATASOTTOSCRIZIONE": [
            "2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04",
            "2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08",
            "2026-01-09", "2026-01-10", "2026-01-11", "2026-01-12",
        ],
        "CREAZIONE_ANTENNA": [
            "2026-01-03", "2026-01-04", "2026-01-06", "2026-01-08",
            "2026-01-07", "2026-01-10", "2026-01-30", "2026-02-05",
            "2026-01-11", "2026-01-12", "2026-01-20", "2026-03-20",
        ],
        "METODOCONSEGNA": ["A", "A", "B", "B", "A", "C", "C", "C", "A", "B", "B", "C"],
        "IDCONTRATTOTLM": [f"C{i:04d}" for i in range(12)],
        "PYID": [f"PY-{i:04d}" for i in range(12)],
        "CONTRATTOID": [1000 + i for i in range(12)],
        "SERIALNUMBER": [f"SN{i:04d}" for i in range(12)],
        "SMARTMOVE": [True] * 11 + [False],
    })


def _activation_df_with_invalid_values():
    return pd.DataFrame({
        "DATASOTTOSCRIZIONE": [
            "2026-01-01",
            "2026-01-02",
            None,
            "non data",
            "2026-01-05",
        ],
        "CREAZIONE_ANTENNA": [
            "2026-01-03",
            "2026-01-10",
            "2026-01-12",
            "2026-01-15",
            "2026-01-04",
        ],
        "METODOCONSEGNA": ["A", "B", "B", "C", "A"],
        "IDCONTRATTOTLM": [f"C{i:04d}" for i in range(5)],
        "PYID": [f"PY-{i:04d}" for i in range(5)],
    })


def test_classifier_recognizes_activation_dates_before_code():
    result = SemanticColumnClassifier().classify_dataframe(_activation_df())

    assert result["DATASOTTOSCRIZIONE"]["semantic_type"] in {"DATE", "DATETIME"}
    assert result["CREAZIONE_ANTENNA"]["semantic_type"] in {"DATE", "DATETIME"}
    assert "parsabili come data" in result["CREAZIONE_ANTENNA"]["reason"]
    assert result["IDCONTRATTOTLM"]["semantic_type"] == "IDENTIFIER"


def test_parse_datetime_series_handles_valid_null_and_unparseable_values():
    engine = SemanticFeatureEngineeringEngine()
    parsed = engine.parse_datetime_series(pd.Series([
        "2026-01-01",
        None,
        "non data",
        20260104,
        20260105103000,
        44562,
    ]))

    assert parsed.notna().sum() == 4
    assert pd.isna(parsed.iloc[1])
    assert pd.isna(parsed.iloc[2])


def test_duration_feature_preserves_rows_float_nan_and_negative_warning():
    df = _activation_df_with_invalid_values()
    engine = SemanticFeatureEngineeringEngine()
    plan = engine.build_feature_plan(REQUEST, df)
    enriched, results = engine.apply_feature_plan(df, plan)
    duration = enriched["TEMPO_ATTIVAZIONE_GIORNI"]
    feature = results["features"][0]

    assert len(enriched) == len(df)
    assert pd.api.types.is_float_dtype(duration)
    assert duration.tolist()[0] == 2
    assert duration.tolist()[1] == 8
    assert pd.isna(duration.tolist()[2])
    assert pd.isna(duration.tolist()[3])
    assert duration.tolist()[4] == -1
    assert feature["missing_count"] == 2
    assert feature["negative_duration_count"] == 1
    assert any(item["warning"] == "negative_duration" for item in results["warnings"])


def test_activation_time_feature_is_created_with_audit():
    df = _activation_df()
    engine = SemanticFeatureEngineeringEngine()
    plan = engine.build_feature_plan(REQUEST, df, SemanticColumnClassifier().classify_dataframe(df))
    enriched, results = engine.apply_feature_plan(df, plan)

    assert "TEMPO_ATTIVAZIONE_GIORNI" in enriched.columns
    assert results["features"][0]["feature_name"] == "TEMPO_ATTIVAZIONE_GIORNI"
    assert results["features"][0]["status"] == "created"
    assert results["features"][0]["source_columns"] == {
        "start": "DATASOTTOSCRIZIONE",
        "end": "CREAZIONE_ANTENNA",
    }
    assert results["features"][0]["valid_count"] == len(df)
    assert results["features"][0]["negative_duration_count"] == 0
    assert enriched["TEMPO_ATTIVAZIONE_GIORNI"].iloc[0] == 2
    assert pd.api.types.is_float_dtype(enriched["TEMPO_ATTIVAZIONE_GIORNI"])


def test_activation_charts_include_distribution_boxplot_trend_and_method_segmentation():
    engine = SemanticFeatureEngineeringEngine()
    df, _ = engine.apply_feature_plan(
        _activation_df(),
        engine.build_feature_plan(REQUEST, _activation_df()),
    )

    payload = ChartGenerator.generate_dashboard_charts(df, insights={})
    titles = [chart.layout.title.text for chart in payload["charts"]]
    skipped = {item["column"]: item for item in payload["skipped_charts"]}

    assert any("Distribuzione tempi di attivazione" in title for title in titles)
    assert any("Boxplot tempi di attivazione" in title for title in titles)
    assert any("Trend medio/mediano tempi attivazione" in title for title in titles)
    assert any("Tempi di attivazione per METODOCONSEGNA" in title for title in titles)
    assert skipped["IDCONTRATTOTLM"]["semantic_type"] == "IDENTIFIER"
    assert skipped["PYID"]["semantic_type"] == "IDENTIFIER"


def test_business_insights_describe_activation_distribution_and_excluded_ids():
    engine = SemanticFeatureEngineeringEngine()
    df, results = engine.apply_feature_plan(
        _activation_df(),
        engine.build_feature_plan(REQUEST, _activation_df()),
    )

    insights = BusinessInsightGenerator().generate_activation_time_insights(df, results)

    assert any("mediana dei tempi di attivazione" in item for item in insights)
    assert any("P95" in item for item in insights)
    assert any("Sono stati esclusi ID" in item for item in insights)


def test_complete_pipeline_uses_activation_feature_in_report(monkeypatch, tmp_path):
    manager = AnalysisHistoryManager(db_path=tmp_path / "analysis_history.db")
    monkeypatch.setattr(data_processor_module, "AnalysisHistoryManager", lambda: manager)

    processor = DataProcessorAgent.__new__(DataProcessorAgent)
    processor.name = "DataProcessor"
    processor.log = lambda message: None
    processor.build_prompt_with_skill = lambda prompt: prompt
    processor.call_openai = lambda messages: "report deterministico"

    analyst = AnalystAgent.__new__(AnalystAgent)
    analyst.name = "Analyst"
    analyst.local_engine = SeniorDataAnalystEngine()
    analyst.client = None
    analyst.log = lambda message: None

    reporter = ReportGeneratorAgent.__new__(ReportGeneratorAgent)
    reporter.name = "ReportGenerator"
    reporter.local_engine = SeniorDataAnalystEngine()
    reporter.client = None
    reporter.log = lambda message: None

    context = AgentContext(
        user_input=REQUEST,
        raw_data={"dataframe": _activation_df()},
        metadata={"source_type": "excel"},
    )

    context = processor.process(context)
    context = analyst.process(context)
    context = reporter.process(context)

    assert context.is_valid is True
    assert context.errors == []
    assert context.processed_data
    assert "TEMPO_ATTIVAZIONE_GIORNI" in context.raw_data["dataframe"].columns
    assert context.processed_data["semantic_feature_results"]["features"][0]["status"] == "created"
    assert (
        "TEMPO_ATTIVAZIONE_GIORNI"
        in context.processed_data["advanced_statistical_results"].get("numeric_analysis", {})
        or "TEMPO_ATTIVAZIONE_GIORNI" in context.processed_data["engineered_features"]
    )
    assert context.processed_data["dataframe_enriched_metadata"]["row_count"] > 0
    assert context.processed_data["semantic_columns"]["CREAZIONE_ANTENNA"]["semantic_type"] in {"DATE", "DATETIME"}
    assert "Media IDCONTRATTOTLM" not in context.final_report
    assert "top PYID" not in context.final_report.lower()
    assert "0 righe, 0 colonne" not in context.final_report
    assert "TEMPO_ATTIVAZIONE_GIORNI" in context.final_report
    assert "mediana" in context.final_report.lower()
    assert "P95" in context.final_report


def test_pdf_generator_writes_non_empty_pdf(tmp_path):
    output_path = tmp_path / "activation_report.pdf"
    success = PDFGenerator().generate_report(
        output_path=str(output_path),
        user_input=REQUEST,
        context={
            "raw_data": {"row_count": 2, "columns": ["A"]},
            "processed_data": {},
            "insights": {"summary": "ok"},
            "final_report": "# Report\nTEMPO_ATTIVAZIONE_GIORNI",
            "is_valid": True,
            "errors": [],
        },
        charts_figures=[],
        title="Activation Report",
    )

    assert success is True
    assert output_path.suffix == ".pdf"
    assert output_path.stat().st_size > 0
