import json

import pandas as pd

from services.analysis_engine import AnalysisEngine, AnalysisPlan
from services.semantic_memory import SemanticMemory
from utils.analysis_history_manager import AnalysisHistoryManager


class StaticSemanticMemory(SemanticMemory):
    def __init__(self, vectors):
        super().__init__(client=None)
        self.vectors = vectors

    def embed_text(self, text: str):
        vector = self.vectors.get(text)
        return self.normalize_vector(vector) if vector is not None else None


def test_count_occurrences_by_category_is_deterministic_and_json_safe():
    df = pd.DataFrame({
        "stato": ["open", "closed", "open", None],
        "amount": [10, 20, 30, 40],
    })
    engine = AnalysisEngine()

    payload = engine.run(
        "conta occorrenze per stato",
        df,
        plan=AnalysisPlan(
            analysis_type="count_occurrences",
            target_column="stato",
            limit=10,
        ),
    )

    counts = payload["deterministic_results"]["counts"]
    assert counts == [
        {"value": "open", "count": 2},
        {"value": "closed", "count": 1},
        {"value": "N/D", "count": 1},
    ]
    json.dumps(payload)


def test_business_count_request_selects_contract_status_and_related_antenna_counts():
    df = pd.DataFrame({
        "CONTRATTOID": [1, 2, 3, 4],
        "STATO_CONTRATTO": ["ATTIVO", "ATTIVO", "NON_ATTIVO", "ATTIVO"],
        "STATO_ANTENNA": ["ATTIVA", "ASSENTE", "ATTIVA", "ATTIVA"],
        "AGG_ANTENNA": ["A1", "N/D", "A2", "A3"],
    })

    payload = AnalysisEngine().run(
        "Dimmi il numero totale di contratti attivi, quelli non attivi e le relative antenne",
        df,
    )

    result = payload["deterministic_results"]
    assert payload["execution_summary"]["row_count"] == 4
    assert payload["analysis_plan"]["analysis_type"] == "count_occurrences"
    assert result["target_column"] == "STATO_CONTRATTO"
    assert result["total_records"] == 4
    assert result["counts"] == [
        {"value": "ATTIVO", "count": 3},
        {"value": "NON_ATTIVO", "count": 1},
    ]
    assert {item["target_column"] for item in result["related_counts"]} >= {
        "STATO_ANTENNA", "AGG_ANTENNA",
    }


def test_request_builds_generic_semantic_groups_and_cross_tab():
    df = pd.DataFrame({
        "PRIORITA": [
            "CRITICA", "CRITICA", "CRITICA", "CRITICA", "CRITICA",
            "ALTA", "MEDIA", "BASSA",
        ],
        "CANALE": [
            "WEB", "WEB", "APP", None, "NEGOZIO",
            "WEB", None, "APP",
        ],
    })

    payload = AnalysisEngine().run(
        "Quanti elementi hanno priorità CRITICA, quanti non CRITICA e il relativo CANALE?",
        df,
    )

    result = payload["deterministic_results"]
    assert result["counts"] == [
        {"value": "CRITICA", "count": 5},
        {"value": "NON CRITICA", "count": 3},
    ]
    assert result["semantic_groups"][1] == {
        "label": "NON CRITICA",
        "operator": "exclude",
        "values": ["CRITICA"],
        "source_values": ["ALTA", "BASSA", "MEDIA"],
        "count": 3,
    }
    cross_tab = next(
        item for item in result["cross_tabs"]
        if item["related_column"] == "CANALE"
    )
    assert cross_tab["total_records"] == 8
    assert cross_tab["rows"] == [
        {
            "value": "CRITICA",
            "total": 5,
            "counts": {"APP": 1, "N/D": 1, "NEGOZIO": 1, "WEB": 2},
            "shares_percent": {"APP": 20.0, "N/D": 20.0, "NEGOZIO": 20.0, "WEB": 40.0},
        },
        {
            "value": "NON CRITICA",
            "total": 3,
            "counts": {"APP": 1, "N/D": 1, "NEGOZIO": 0, "WEB": 1},
            "shares_percent": {"APP": 33.33, "N/D": 33.33, "NEGOZIO": 0.0, "WEB": 33.33},
        },
    ]
    assert sum(item["total"] for item in cross_tab["rows"]) == len(df)


def test_generic_semantic_group_supports_inflected_request_terms():
    df = pd.DataFrame({"CLASSE": ["URGENTE", "URGENTE", "ORDINARIA"]})

    result = AnalysisEngine().run(
        "Quanti casi sono urgenti e quanti non urgenti?", df
    )["deterministic_results"]

    assert result["counts"] == [
        {"value": "URGENTE", "count": 2},
        {"value": "NON URGENTE", "count": 1},
    ]


def test_top_n_values_by_numeric_sum():
    df = pd.DataFrame({
        "cliente": ["A", "A", "B", "C"],
        "fatturato": [10, 15, 40, 5],
    })
    engine = AnalysisEngine()

    result = engine.execute_plan(
        df,
        AnalysisPlan(
            analysis_type="top_n",
            target_column="cliente",
            value_column="fatturato",
            aggregation="sum",
            limit=2,
        ),
    )

    assert result["top"] == [
        {"value": "B", "metric": 40},
        {"value": "A", "metric": 25},
    ]


def test_numeric_aggregation_mean_grouped_by_category():
    df = pd.DataFrame({
        "area": ["Nord", "Nord", "Sud"],
        "score": [10, 20, 40],
    })
    engine = AnalysisEngine()

    result = engine.execute_plan(
        df,
        AnalysisPlan(
            analysis_type="numeric_aggregation",
            group_by_column="area",
            value_column="score",
            aggregation="mean",
        ),
    )

    assert result["groups"] == [
        {"group": "Sud", "value": 40.0},
        {"group": "Nord", "value": 15.0},
    ]


def test_time_trend_counts_rows_by_day():
    df = pd.DataFrame({
        "data_evento": ["2026-01-01", "2026-01-01", "2026-01-02"],
        "stato": ["open", "closed", "open"],
    })
    engine = AnalysisEngine()

    result = engine.execute_plan(
        df,
        AnalysisPlan(
            analysis_type="time_trend",
            time_column="data_evento",
            aggregation="count",
        ),
    )

    assert result["frequency"] == "D"
    assert result["points"] == [
        {"period": "2026-01-01T00:00:00", "value": 2},
        {"period": "2026-01-02T00:00:00", "value": 1},
    ]


def test_null_and_duplicate_detection():
    df = pd.DataFrame({
        "categoria": ["A", "A", None, "B", "B"],
        "valore": [1, 1, 2, None, None],
    })
    engine = AnalysisEngine()

    nulls = engine.execute_plan(df, AnalysisPlan(analysis_type="null_detection"))
    duplicates = engine.execute_plan(df, AnalysisPlan(analysis_type="duplicate_detection"))

    assert nulls["total_nulls"] == 3
    assert {"column": "valore", "null_count": 2, "null_percent": 40.0} in nulls["columns_with_nulls"]
    assert duplicates["duplicate_rows"] == 2


def test_engine_returns_new_pattern_metadata(tmp_path):
    manager = AnalysisHistoryManager(db_path=tmp_path / "analysis_history.db")
    df = pd.DataFrame({"stato": ["open", "closed", "open"]})
    engine = AnalysisEngine(history_manager=manager)

    payload = engine.run("conta ticket per stato", df, source_type="csv")

    assert payload["plan_source"] == "new"
    assert payload["analysis_pattern_id"] is not None
    assert payload["confidence_score"] == 0.0
    assert payload["similarity_score"] is None
    saved = manager.get_pattern(payload["analysis_pattern_id"])
    assert saved["confidence_score"] == 0.0


def test_engine_reuses_high_feedback_pattern_with_scores(tmp_path):
    manager = AnalysisHistoryManager(db_path=tmp_path / "analysis_history.db")
    pattern_id = manager.add_pattern(
        description="conta ticket per stato",
        source_type="csv",
        analysis_plan=AnalysisPlan(
            analysis_type="count_occurrences",
            target_column="stato",
        ).to_dict(),
        columns_used=["stato"],
        feedback_score=0.95,
        success=True,
    )
    df = pd.DataFrame({"stato": ["open", "closed", "open"]})
    engine = AnalysisEngine(history_manager=manager)

    payload = engine.run("conteggio ticket per stato", df, source_type="csv")

    assert payload["plan_source"] == "history"
    assert payload["analysis_pattern_id"] == pattern_id
    assert payload["similarity_score"] >= 0.65
    assert payload["confidence_score"] > 0.0


def test_engine_propagates_embedding_similarity_method(tmp_path):
    memory = StaticSemanticMemory({
        "mostrami i ticket per stato": [1, 0],
        "quanti ticket ci sono per ogni stato": [0.95, 0.05],
    })
    manager = AnalysisHistoryManager(db_path=tmp_path / "analysis_history.db", semantic_memory=memory)
    pattern_id = manager.add_pattern(
        description="mostrami i ticket per stato",
        source_type="csv",
        analysis_plan=AnalysisPlan(analysis_type="count_occurrences", target_column="stato").to_dict(),
        columns_used=["stato"],
        feedback_score=0.95,
        success=True,
    )
    df = pd.DataFrame({"stato": ["open", "closed", "open"]})
    engine = AnalysisEngine(history_manager=manager)

    payload = engine.run("quanti ticket ci sono per ogni stato", df, source_type="csv")

    assert payload["plan_source"] == "history"
    assert payload["analysis_pattern_id"] == pattern_id
    assert payload["similarity_method"] == "embedding"
    assert payload["similarity_score"] > 0.9
    assert payload["execution_summary"]["similarity_method"] == "embedding"
