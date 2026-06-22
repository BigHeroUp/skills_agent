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


def test_analysis_history_saves_and_recovers_pattern(tmp_path):
    manager = AnalysisHistoryManager(db_path=tmp_path / "analysis_history.db")
    plan = AnalysisPlan(
        analysis_type="count_occurrences",
        target_column="stato",
        limit=5,
        description="Conteggio ticket per stato",
    )

    pattern_id = manager.add_pattern(
        description="conta ticket per stato",
        source_type="csv",
        analysis_plan=plan.to_dict(),
        columns_used=["stato"],
        feedback_score=0.9,
        success=True,
    )

    matches = manager.find_similar_patterns(
        description="conteggio ticket per stato",
        source_type="csv",
        similarity_threshold=0.5,
        min_feedback_score=0.8,
    )

    assert matches[0]["id"] == pattern_id
    assert matches[0]["analysis_plan"]["analysis_type"] == "count_occurrences"
    assert matches[0]["columns_used"] == ["stato"]
    assert matches[0]["similarity_method"] == "text"


def test_analysis_engine_reuses_similar_positive_pattern(tmp_path):
    manager = AnalysisHistoryManager(db_path=tmp_path / "analysis_history.db")
    plan = AnalysisPlan(
        analysis_type="top_n",
        target_column="cliente",
        value_column="fatturato",
        aggregation="sum",
        limit=3,
        description="Top clienti per fatturato",
    )
    manager.add_pattern(
        description="mostra top clienti per fatturato",
        source_type="excel",
        analysis_plan=plan.to_dict(),
        columns_used=["cliente", "fatturato"],
        feedback_score=0.95,
        success=True,
    )

    engine = AnalysisEngine(history_manager=manager)
    inferred = engine.infer_plan(
        "mostrami i top clienti per fatturato",
        df=None,
        source_type="excel",
    )

    assert inferred.analysis_type == "top_n"
    assert inferred.target_column == "cliente"
    assert inferred.value_column == "fatturato"
    assert inferred.aggregation == "sum"


def test_new_pattern_starts_with_zero_confidence(tmp_path):
    manager = AnalysisHistoryManager(db_path=tmp_path / "analysis_history.db")
    plan = AnalysisPlan(analysis_type="count_occurrences", target_column="stato")

    pattern_id = manager.add_pattern(
        description="conta per stato",
        source_type="csv",
        analysis_plan=plan.to_dict(),
        columns_used=["stato"],
        feedback_score=0.0,
        success=False,
    )

    pattern = manager.get_pattern(pattern_id)
    assert pattern["execution_count"] == 1
    assert pattern["success_count"] == 0
    assert pattern["feedback_score"] == 0.0
    assert pattern["confidence_score"] == 0.0


def test_positive_feedback_increases_success_and_confidence(tmp_path):
    manager = AnalysisHistoryManager(db_path=tmp_path / "analysis_history.db")
    pattern_id = manager.add_pattern(
        description="conta ticket per stato",
        source_type="csv",
        analysis_plan=AnalysisPlan(analysis_type="count_occurrences", target_column="stato").to_dict(),
        columns_used=["stato"],
    )

    updated = manager.update_feedback(pattern_id, success=True, feedback_score=1.0)

    assert updated["execution_count"] == 2
    assert updated["success_count"] == 1
    assert updated["feedback_score"] == 1.0
    assert updated["confidence_score"] > 0.0


def test_negative_feedback_increases_execution_not_success(tmp_path):
    manager = AnalysisHistoryManager(db_path=tmp_path / "analysis_history.db")
    pattern_id = manager.add_pattern(
        description="conta ticket per stato",
        source_type="csv",
        analysis_plan=AnalysisPlan(analysis_type="count_occurrences", target_column="stato").to_dict(),
        columns_used=["stato"],
    )

    updated = manager.update_feedback(pattern_id, success=False, feedback_score=0.15)

    assert updated["execution_count"] == 2
    assert updated["success_count"] == 0
    assert updated["feedback_score"] == 0.15


def test_low_feedback_pattern_is_not_reused(tmp_path):
    manager = AnalysisHistoryManager(db_path=tmp_path / "analysis_history.db")
    manager.add_pattern(
        description="mostra top clienti per fatturato",
        source_type="excel",
        analysis_plan=AnalysisPlan(
            analysis_type="top_n",
            target_column="cliente",
            value_column="fatturato",
            aggregation="sum",
        ).to_dict(),
        columns_used=["cliente", "fatturato"],
        feedback_score=0.2,
        success=False,
    )

    matches = manager.find_similar_patterns(
        "mostrami i top clienti per fatturato",
        "excel",
        similarity_threshold=0.5,
        min_feedback_score=0.6,
    )

    assert matches == []


def test_db_migration_adds_embedding_column(tmp_path):
    db_path = tmp_path / "analysis_history.db"
    import sqlite3

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE analysis_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                source_type TEXT NOT NULL,
                analysis_plan TEXT NOT NULL,
                columns_used TEXT NOT NULL,
                feedback_score REAL DEFAULT 0.0,
                execution_count INTEGER DEFAULT 1,
                success_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                last_used TEXT NOT NULL,
                notes TEXT
            )
        """)
        conn.commit()

    AnalysisHistoryManager(db_path=db_path)

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(analysis_history)")
        columns = {row[1] for row in cursor.fetchall()}

    assert "embedding_json" in columns
    assert "confidence_score" in columns


def test_pattern_is_saved_with_embedding_json(tmp_path):
    memory = StaticSemanticMemory({"conta ticket per stato": [1, 0]})
    manager = AnalysisHistoryManager(db_path=tmp_path / "analysis_history.db", semantic_memory=memory)

    pattern_id = manager.add_pattern(
        description="conta ticket per stato",
        source_type="csv",
        analysis_plan=AnalysisPlan(analysis_type="count_occurrences", target_column="stato").to_dict(),
        columns_used=["stato"],
    )

    pattern = manager.get_pattern(pattern_id)
    assert pattern["embedding_json"] == "[1.0, 0.0]"


def test_similarity_uses_embedding_when_available(tmp_path):
    memory = StaticSemanticMemory({
        "mostrami i ticket per stato": [1, 0],
        "distribuzione dei ticket per stato": [0.9, 0.1],
    })
    manager = AnalysisHistoryManager(db_path=tmp_path / "analysis_history.db", semantic_memory=memory)
    manager.add_pattern(
        description="mostrami i ticket per stato",
        source_type="csv",
        analysis_plan=AnalysisPlan(analysis_type="count_occurrences", target_column="stato").to_dict(),
        columns_used=["stato"],
        feedback_score=0.9,
        success=True,
    )

    matches = manager.find_similar_patterns(
        "distribuzione dei ticket per stato",
        "csv",
        similarity_threshold=0.8,
        min_feedback_score=0.6,
    )

    assert matches[0]["similarity_method"] == "embedding"
    assert matches[0]["similarity_score"] > 0.9


def test_similarity_falls_back_to_text_when_embedding_unavailable(tmp_path):
    memory = StaticSemanticMemory({})
    manager = AnalysisHistoryManager(db_path=tmp_path / "analysis_history.db", semantic_memory=memory)
    manager.add_pattern(
        description="conta ticket per stato",
        source_type="csv",
        analysis_plan=AnalysisPlan(analysis_type="count_occurrences", target_column="stato").to_dict(),
        columns_used=["stato"],
        feedback_score=0.9,
        success=True,
    )

    matches = manager.find_similar_patterns(
        "conteggio ticket per stato",
        "csv",
        similarity_threshold=0.5,
        min_feedback_score=0.6,
    )

    assert matches[0]["similarity_method"] == "text"
