import pandas as pd

from core.capabilities import CategoricalCountCapability
from core.kernel.bootstrap import create_default_kernel
from core.kernel.capability import CapabilityRequest
from services.kernel_analysis_parity import KernelAnalysisParityRunner


def _records():
    return pd.DataFrame({
        "PRIORITA": ["CRITICA", "CRITICA", "ALTA", "MEDIA"],
        "CANALE": ["WEB", "APP", "WEB", None],
    })


def test_kernel_categorical_count_returns_semantic_cross_tab():
    response = create_default_kernel().execute_capability(
        "analysis.categorical_count",
        payload={
            "question": "Per PRIORITA, quanti elementi sono CRITICI, non CRITICI e il relativo CANALE?",
            "records": _records().to_dict(orient="records"),
        },
    )

    assert response.success is True
    result = response.result["deterministic_results"]
    assert result["counts"] == [
        {"value": "CRITICA", "count": 2},
        {"value": "NON CRITICA", "count": 2},
    ]
    assert result["cross_tabs"][0]["total_records"] == 4
    assert response.metadata["execution_type"] == "deterministic_categorical_count"


def test_kernel_categorical_count_validates_payload():
    capability = CategoricalCountCapability()
    response = capability.execute(CapabilityRequest(
        capability_name="analysis.categorical_count",
        payload={"question": "conta", "records": []},
    ))

    assert response.success is False
    assert response.metadata["error_type"] == "ValidationError"


def test_kernel_shadow_runner_matches_production_engine():
    comparison = KernelAnalysisParityRunner().compare(
        "Per PRIORITA, quanti elementi sono CRITICI, non CRITICI e il relativo CANALE?",
        _records(),
    )

    assert comparison["matched"] is True
    assert comparison["status"] == "matched"
    assert comparison["mismatched_fields"] == []


def test_kernel_shadow_runner_matches_multiple_analysis_contracts():
    dataframe = pd.DataFrame({
        "segmento": ["A", "A", "B", "B"],
        "valore": [10.0, 5.0, 8.0, None],
        "data": ["2026-01-01", "2026-01-02", "2026-02-01", "2026-02-02"],
    })
    questions = (
        "Calcola la somma di valore per segmento",
        "Top 2 segmento per somma di valore",
        "Trova tutti i valori mancanti",
        "Individua le righe duplicate",
        "Mostra il trend mensile di valore per data",
    )

    comparisons = [KernelAnalysisParityRunner().compare(question, dataframe) for question in questions]

    assert all(item["matched"] for item in comparisons)
    assert {item["kernel"]["analysis_plan"]["analysis_type"] for item in comparisons} == {
        "numeric_aggregation", "top_n", "null_detection", "duplicate_detection", "time_trend"
    }
