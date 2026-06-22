"""Storico locale per pattern analitici riutilizzabili."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from services.semantic_memory import SemanticMemory
from utils.logging_config import get_logger


logger = get_logger("analysis_history_manager")


class AnalysisHistoryManager:
    """Memorizza e recupera piani analitici eseguiti con feedback positivo."""

    DB_PATH = Path("data") / "analysis_history.db"

    def __init__(self, db_path: str | Path | None = None, semantic_memory: SemanticMemory | None = None):
        self.db_path = Path(db_path) if db_path else self.DB_PATH
        self.semantic_memory = semantic_memory or SemanticMemory()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    description TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    analysis_plan TEXT NOT NULL,
                    columns_used TEXT NOT NULL,
                    embedding_json TEXT,
                    feedback_score REAL DEFAULT 0.0,
                    confidence_score REAL DEFAULT 0.0,
                    execution_count INTEGER DEFAULT 1,
                    success_count INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    last_used TEXT NOT NULL,
                    notes TEXT
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_analysis_history_source
                ON analysis_history(source_type)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_analysis_history_description
                ON analysis_history(description)
            """)
            self._ensure_column(cursor, "analysis_history", "confidence_score", "REAL DEFAULT 0.0")
            self._ensure_column(cursor, "analysis_history", "embedding_json", "TEXT")
            conn.commit()

    def _ensure_column(self, cursor, table_name: str, column_name: str, definition: str):
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = {row[1] for row in cursor.fetchall()}
        if column_name not in columns:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")

    def add_pattern(
        self,
        description: str,
        source_type: str,
        analysis_plan: dict[str, Any],
        columns_used: list[str],
        feedback_score: float = 0.0,
        success: bool = False,
        notes: str = "",
    ) -> int:
        """Salva un pattern analitico e ritorna l'id."""
        now = datetime.now().isoformat()
        embedding = self.semantic_memory.embed_text(description)
        embedding_json = json.dumps(embedding) if embedding is not None else None
        execution_count = 1
        success_count = 1 if success else 0
        confidence_score = self._compute_confidence(
            execution_count=execution_count,
            success_count=success_count,
            feedback_score=feedback_score,
        )
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO analysis_history
                (
                    description,
                    source_type,
                    analysis_plan,
                    columns_used,
                    embedding_json,
                    feedback_score,
                    confidence_score,
                    execution_count,
                    success_count,
                    created_at,
                    last_used,
                    notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                description,
                source_type,
                json.dumps(analysis_plan, ensure_ascii=False),
                json.dumps(columns_used, ensure_ascii=False),
                embedding_json,
                float(feedback_score),
                confidence_score,
                execution_count,
                success_count,
                now,
                now,
                notes,
            ))
            conn.commit()
            pattern_id = int(cursor.lastrowid)
            logger.info("Pattern analitico salvato. id=%s source_type=%s", pattern_id, source_type)
            return pattern_id

    def find_similar_patterns(
        self,
        description: str,
        source_type: str,
        similarity_threshold: float = 0.6,
        min_feedback_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Trova pattern simili ordinati per similarita e qualita feedback."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    id,
                    description,
                    source_type,
                    analysis_plan,
                    columns_used,
                    embedding_json,
                    feedback_score,
                    confidence_score,
                    execution_count,
                    success_count,
                    created_at,
                    last_used,
                    notes
                FROM analysis_history
                WHERE source_type = ? AND feedback_score >= ?
                ORDER BY feedback_score DESC, execution_count DESC
            """, (source_type, min_feedback_score))
            rows = cursor.fetchall()

        matches = []
        query_embedding = self.semantic_memory.embed_text(description)
        for row in rows:
            stored_embedding = self._load_or_create_embedding(row[0], row[1], row[5])
            if query_embedding is not None and stored_embedding is not None:
                similarity = self.semantic_memory.cosine_similarity(query_embedding, stored_embedding)
                similarity_method = "embedding"
            else:
                similarity = self._compute_similarity(description, row[1])
                similarity_method = "text"
            if similarity < similarity_threshold:
                continue
            matches.append({
                "id": row[0],
                "description": row[1],
                "source_type": row[2],
                "analysis_plan": json.loads(row[3]),
                "columns_used": json.loads(row[4]),
                "embedding_json": row[5],
                "feedback_score": row[6],
                "confidence_score": row[7],
                "execution_count": row[8],
                "success_count": row[9],
                "created_at": row[10],
                "last_used": row[11],
                "notes": row[12],
                "similarity": similarity,
                "similarity_score": similarity,
                "similarity_method": similarity_method,
            })

        matches.sort(
            key=lambda item: (
                item["similarity"],
                item["feedback_score"],
                item["success_count"],
            ),
            reverse=True,
        )
        return matches

    def get_pattern(self, pattern_id: int) -> dict[str, Any] | None:
        """Ritorna un pattern con metriche di feedback e confidence."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    id,
                    description,
                    source_type,
                    analysis_plan,
                    columns_used,
                    embedding_json,
                    feedback_score,
                    confidence_score,
                    execution_count,
                    success_count,
                    created_at,
                    last_used,
                    notes
                FROM analysis_history
                WHERE id = ?
            """, (pattern_id,))
            row = cursor.fetchone()

        if not row:
            return None

        return {
            "id": row[0],
            "description": row[1],
            "source_type": row[2],
            "analysis_plan": json.loads(row[3]),
            "columns_used": json.loads(row[4]),
            "embedding_json": row[5],
            "feedback_score": row[6],
            "confidence_score": row[7],
            "execution_count": row[8],
            "success_count": row[9],
            "created_at": row[10],
            "last_used": row[11],
            "notes": row[12],
        }

    def calculate_confidence_score(self, pattern_id: int) -> float:
        """Calcola e persiste il confidence score del pattern."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT execution_count, success_count, feedback_score
                FROM analysis_history
                WHERE id = ?
            """, (pattern_id,))
            row = cursor.fetchone()
            if not row:
                return 0.0

            confidence_score = self._compute_confidence(
                execution_count=int(row[0]),
                success_count=int(row[1]),
                feedback_score=float(row[2] or 0.0),
            )
            cursor.execute("""
                UPDATE analysis_history
                SET confidence_score = ?
                WHERE id = ?
            """, (confidence_score, pattern_id))
            conn.commit()
            return confidence_score

    def update_feedback(
        self,
        pattern_id: int,
        success: bool,
        feedback_score: float | None = None,
    ):
        """Aggiorna feedback e contatori del pattern."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT execution_count, success_count, feedback_score
                FROM analysis_history
                WHERE id = ?
            """, (pattern_id,))
            row = cursor.fetchone()
            if not row:
                return

            execution_count, success_count, current_score = row
            new_execution_count = int(execution_count) + 1
            new_success_count = int(success_count) + (1 if success else 0)
            success_rate = new_success_count / new_execution_count
            final_score = float(feedback_score) if feedback_score is not None else success_rate
            confidence_score = self._compute_confidence(
                execution_count=new_execution_count,
                success_count=new_success_count,
                feedback_score=final_score,
            )

            cursor.execute("""
                UPDATE analysis_history
                SET execution_count = ?,
                    success_count = ?,
                    feedback_score = ?,
                    confidence_score = ?,
                    last_used = ?
                WHERE id = ?
            """, (
                new_execution_count,
                new_success_count,
                final_score,
                confidence_score,
                datetime.now().isoformat(),
                pattern_id,
            ))
            conn.commit()
            logger.info(
                "Feedback pattern aggiornato. id=%s success=%s score=%.2f",
                pattern_id,
                success,
                final_score,
            )
            return self.get_pattern(pattern_id)

    def record_usage(self, pattern_id: int):
        """Incrementa il numero utilizzi quando un pattern viene riusato."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE analysis_history
                SET execution_count = execution_count + 1,
                    last_used = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), pattern_id))
            conn.commit()
        self.calculate_confidence_score(pattern_id)

    def clear_history(self):
        """Pulisce lo storico. Usato solo nei test."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM analysis_history")
            conn.commit()

    @staticmethod
    def _compute_similarity(left: str, right: str) -> float:
        return SemanticMemory(client=None).text_similarity(left, right)

    def _load_or_create_embedding(self, pattern_id: int, description: str, embedding_json: str | None):
        if embedding_json:
            try:
                return json.loads(embedding_json)
            except json.JSONDecodeError:
                pass

        embedding = self.semantic_memory.embed_text(description)
        if embedding is None:
            return None

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE analysis_history
                SET embedding_json = ?
                WHERE id = ?
            """, (json.dumps(embedding), pattern_id))
            conn.commit()
        return embedding

    @staticmethod
    def _compute_confidence(execution_count: int, success_count: int, feedback_score: float) -> float:
        if execution_count <= 0:
            return 0.0
        success_rate = success_count / execution_count
        sample_factor = min(1.0, execution_count / 5)
        confidence = ((0.6 * feedback_score) + (0.4 * success_rate)) * sample_factor
        return round(max(0.0, min(1.0, confidence)), 4)
