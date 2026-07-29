"""Reproducible, domain-neutral functional benchmark for the deterministic engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from services.analysis_engine import AnalysisEngine


@dataclass(frozen=True)
class DomainFixture:
    domain: str
    dimension: str
    metric: str
    labels: tuple[str, str, str]

    def records(self) -> list[dict[str, Any]]:
        first, second, third = self.labels
        return [
            {self.dimension: first, "canale": "web", self.metric: 10.0},
            {self.dimension: first, "canale": "web", self.metric: 10.0},
            {self.dimension: second, "canale": "app", self.metric: 25.0},
            {self.dimension: third, "canale": "web", self.metric: 5.0},
            {self.dimension: second, "canale": "store", self.metric: None},
        ]


FIXTURES = (
    DomainFixture("retail", "categoria", "ricavo", ("Casa", "Sport", "Libri")),
    DomainFixture("energia", "fascia", "consumo", ("Giorno", "Sera", "Notte")),
    DomainFixture("allenamento", "disciplina", "distanza", ("Corsa", "Nuoto", "Bici")),
    DomainFixture("supporto", "priorita", "durata", ("Alta", "Media", "Bassa")),
    DomainFixture("universita", "corso", "crediti", ("Storia", "Fisica", "Arte")),
    DomainFixture("meteo", "stazione", "temperatura", ("Nord", "Centro", "Sud")),
)


def benchmark_cases() -> list[dict[str, Any]]:
    """Return baseline and adversarial independently specified contracts."""
    cases: list[dict[str, Any]] = []
    for fixture in FIXTURES:
        first, second, third = fixture.labels
        common = {"domain": fixture.domain, "records": fixture.records()}
        cases.extend([
            {
                **common,
                "id": f"{fixture.domain}-count",
                "prompt": f"Conta gli elementi per {fixture.dimension}",
                "expected_type": "count_occurrences",
                "expected": {
                    "target_column": fixture.dimension,
                    "total_records": 5,
                    "counts": [
                        {"value": first, "count": 2},
                        {"value": second, "count": 2},
                        {"value": third, "count": 1},
                    ],
                },
            },
            {
                **common,
                "id": f"{fixture.domain}-sum",
                "prompt": f"Calcola la somma di {fixture.metric} per {fixture.dimension}",
                "expected_type": "numeric_aggregation",
                "expected": {
                    "aggregation": "sum",
                    "group_by_column": fixture.dimension,
                    "value_column": fixture.metric,
                    "groups": [
                        {"group": second, "value": 25.0},
                        {"group": first, "value": 20.0},
                        {"group": third, "value": 5.0},
                    ],
                },
            },
            {
                **common,
                "id": f"{fixture.domain}-top",
                "prompt": f"Top 2 {fixture.dimension} per somma di {fixture.metric}",
                "expected_type": "top_n",
                "expected": {
                    "aggregation": "sum",
                    "target_column": fixture.dimension,
                    "value_column": fixture.metric,
                    "top": [
                        {"value": second, "metric": 25.0},
                        {"value": first, "metric": 20.0},
                    ],
                },
            },
            {
                **common,
                "id": f"{fixture.domain}-nulls",
                "prompt": "Trova tutti i valori mancanti",
                "expected_type": "null_detection",
                "expected": {
                    "row_count": 5,
                    "total_nulls": 1,
                    "columns_with_nulls": [
                        {"column": fixture.metric, "null_count": 1, "null_percent": 20.0}
                    ],
                },
            },
            {
                **common,
                "id": f"{fixture.domain}-duplicates",
                "prompt": "Individua le righe duplicate",
                "expected_type": "duplicate_detection",
                "expected": {
                    "row_count": 5,
                    "duplicate_rows": 1,
                    "duplicate_groups_rows": 2,
                },
            },
        ])
    cases.extend(adversarial_cases())
    return cases


def adversarial_cases() -> list[dict[str, Any]]:
    """Exercise dirty values, edge cases, ambiguity and safe abstention."""
    quality_records = [
        {"segmento": "A", "valore": 10.0, "nota": None},
        {"segmento": "A", "valore": -5.0, "nota": "ok"},
        {"segmento": "B", "valore": 0.0, "nota": ""},
        {"segmento": None, "valore": 25.0, "nota": "ok"},
        {"segmento": "B", "valore": 0.0, "nota": ""},
    ]
    return [
        {"id": "adversarial-null-mixed", "domain": "quality", "records": quality_records,
         "prompt": "Trova i valori mancanti", "expected_type": "null_detection",
         "expected": {"row_count": 5, "total_nulls": 2}},
        {"id": "adversarial-duplicates-zero", "domain": "quality", "records": quality_records,
         "prompt": "Individua le righe duplicate", "expected_type": "duplicate_detection",
         "expected": {"duplicate_rows": 1, "duplicate_groups_rows": 2}},
        {"id": "adversarial-count-null-category", "domain": "quality", "records": quality_records,
         "prompt": "Conta gli elementi per segmento", "expected_type": "count_occurrences",
         "expected": {"total_records": 5, "counts": [
             {"value": "A", "count": 2}, {"value": "B", "count": 2}, {"value": "N/D", "count": 1}
         ]}},
        {"id": "adversarial-sum-negative", "domain": "quality", "records": quality_records,
         "prompt": "Calcola la somma di valore per segmento", "expected_type": "numeric_aggregation",
         "expected": {"aggregation": "sum", "groups": [
             {"group": None, "value": 25.0}, {"group": "A", "value": 5.0}, {"group": "B", "value": 0.0}
         ]}},
        {"id": "adversarial-top-ties", "domain": "quality", "records": quality_records,
         "prompt": "Top 2 segmento per somma di valore", "expected_type": "top_n",
         "expected": {"aggregation": "sum", "top": [
             {"value": None, "metric": 25.0}, {"value": "A", "metric": 5.0}
         ]}},
        {"id": "adversarial-unsupported-prediction", "domain": "safety", "records": quality_records,
         "prompt": "Prevedi con certezza il valore del prossimo anno", "expected_type": "count_occurrences",
         "expected_status": "unsupported", "expected": {"status": "unsupported"}},
        {"id": "adversarial-unsupported-causal", "domain": "safety", "records": quality_records,
         "prompt": "Dimostra che il segmento causa il risultato", "expected_type": "count_occurrences",
         "expected_status": "unsupported", "expected": {"status": "unsupported"}},
        {"id": "adversarial-all-null-metric", "domain": "quality",
         "records": [{"gruppo": "A", "misura": None}, {"gruppo": "B", "misura": None}],
         "prompt": "Trova tutti i valori mancanti", "expected_type": "null_detection",
         "expected": {"row_count": 2, "total_nulls": 2}},
        {"id": "adversarial-unicode-category", "domain": "localization",
         "records": [{"città": "Forlì"}, {"città": "Forlì"}, {"città": "L'Aquila"}],
         "prompt": "Conta gli elementi per città", "expected_type": "count_occurrences",
         "expected": {"counts": [{"value": "Forlì", "count": 2}, {"value": "L'Aquila", "count": 1}]}},
        {"id": "adversarial-single-row", "domain": "boundaries",
         "records": [{"categoria": "unica", "valore": 0}],
         "prompt": "Conta gli elementi per categoria", "expected_type": "count_occurrences",
         "expected": {"total_records": 1, "counts": [{"value": "unica", "count": 1}]}},
    ]


def _contains(actual: Any, expected: Any) -> bool:
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(
            key in actual and _contains(actual[key], value) for key, value in expected.items()
        )
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(
            _contains(left, right) for left, right in zip(actual, expected)
        )
    return actual == expected


def run_functional_benchmark() -> dict[str, Any]:
    engine = AnalysisEngine()
    results = []
    for case in benchmark_cases():
        payload = engine.run(case["prompt"], pd.DataFrame(case["records"]), source_type="benchmark")
        actual = payload["deterministic_results"]
        inferred_type = payload["analysis_plan"]["analysis_type"]
        expected_status = case.get("expected_status")
        status_matches = not expected_status or actual.get("status") == expected_status
        passed = inferred_type == case["expected_type"] and status_matches and _contains(actual, case["expected"])
        results.append({
            "id": case["id"],
            "domain": case["domain"],
            "passed": passed,
            "expected_type": case["expected_type"],
            "actual_type": inferred_type,
        })
    passed = sum(item["passed"] for item in results)
    domains = len({item["domain"] for item in results})
    return {
        "status": "passed" if passed == len(results) else "failed",
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "domains": domains,
        "results": results,
    }
