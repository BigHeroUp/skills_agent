"""Second pre-beta adversarial campaign across ingestion, intent and safety boundaries."""

from __future__ import annotations

import io
from typing import Callable

import pandas as pd

from services.analysis_engine import AnalysisEngine
from services.platform.robust_ingestion import load_tabular_upload
from services.semantic_column_classifier import SemanticColumnClassifier


def run_adversarial_campaign_v2() -> dict:
    engine = AnalysisEngine()
    checks: list[tuple[str, str, Callable[[], bool]]] = [
        ("ADV2-001", "csv_semicolon", lambda: load_tabular_upload(b"a;b\n1;2\n", "x.csv", max_rows=5).dataframe.shape == (1, 2)),
        ("ADV2-002", "csv_tab", lambda: load_tabular_upload(b"a\tb\n1\t2\n", "x.csv", max_rows=5).dataframe.shape == (1, 2)),
        ("ADV2-003", "csv_cp1252", lambda: load_tabular_upload("città;v\nForlì;1".encode("cp1252"), "x.csv", max_rows=5).warnings != []),
        ("ADV2-004", "empty_file", lambda: raises(lambda: load_tabular_upload(b"", "x.csv", max_rows=5), "vuoto")),
        ("ADV2-005", "unsupported_extension", lambda: raises(lambda: load_tabular_upload(b"x", "x.txt", max_rows=5), "supportati")),
        ("ADV2-006", "row_limit", lambda: raises(lambda: load_tabular_upload(b"a\n1\n2\n", "x.csv", max_rows=1), "record")),
        ("ADV2-007", "column_limit", lambda: raises(lambda: load_tabular_upload(b"a,b,c\n1,2,3", "x.csv", max_rows=5, max_columns=2), "colonne")),
        ("ADV2-008", "corrupt_xlsx", lambda: raises(lambda: load_tabular_upload(b"PK-corrupt", "x.xlsx", max_rows=5), "Excel")),
        ("ADV2-009", "italian_date", lambda: parsed_date("03/07/2026") == pd.Timestamp("2026-07-03")),
        ("ADV2-010", "iso_datetime", lambda: parsed_date("2026-07-03T14:30:00") == pd.Timestamp("2026-07-03T14:30:00")),
        ("ADV2-011", "invalid_date", lambda: pd.isna(parsed_date("31/02/2026"))),
        ("ADV2-012", "unicode_count", lambda: result(engine, "Conta per città", [{"città":"Forlì"},{"città":"L'Aquila"}])["counts"][0]["count"] == 1),
        ("ADV2-013", "null_category_contract", lambda: result(engine, "Conta per gruppo", [{"gruppo":"A"},{"gruppo":None}])["unique_values"] == 2),
        ("ADV2-014", "negative_sum", lambda: result(engine, "Somma valore per gruppo", [{"gruppo":"A","valore":10},{"gruppo":"A","valore":-15}])["groups"][0]["value"] == -5),
        ("ADV2-015", "zero_sum", lambda: result(engine, "Somma valore per gruppo", [{"gruppo":"A","valore":0}])["groups"][0]["value"] == 0),
        ("ADV2-016", "single_row", lambda: result(engine, "Conta per gruppo", [{"gruppo":"A"}])["total_records"] == 1),
        ("ADV2-017", "unsupported_causality", lambda: result(engine, "Dimostra che A causa B", [{"A":1,"B":2}])["status"] == "unsupported"),
        ("ADV2-018", "unsupported_prediction", lambda: result(engine, "Prevedi con certezza il futuro", [{"A":1}])["status"] == "unsupported"),
        ("ADV2-019", "duplicate_with_empty", lambda: result(engine, "Trova duplicati", [{"a":"","b":0},{"a":"","b":0}])["duplicate_rows"] == 1),
        ("ADV2-020", "all_null_quality", lambda: result(engine, "Trova valori mancanti", [{"a":None},{"a":None}])["total_nulls"] == 2),
    ]
    rows = []
    for case_id, category, check in checks:
        try:
            passed = bool(check())
            error = None
        except Exception as exc:
            passed, error = False, f"{type(exc).__name__}: {exc}"
        rows.append({"id": case_id, "category": category, "passed": passed, "error": error})
    passed = sum(item["passed"] for item in rows)
    return {"status": "passed" if passed == len(rows) else "failed", "total": len(rows), "passed": passed, "failed": len(rows)-passed, "results": rows}


def result(engine: AnalysisEngine, prompt: str, records: list[dict]) -> dict:
    return engine.run(prompt, pd.DataFrame(records))["deterministic_results"]


def parsed_date(value: str):
    return SemanticColumnClassifier()._parse_datetime_candidate(pd.Series([value])).iloc[0]


def raises(callable_, message: str) -> bool:
    try:
        callable_()
    except ValueError as exc:
        return message.lower() in str(exc).lower()
    return False
