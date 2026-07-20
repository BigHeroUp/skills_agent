"""
QueryHistoryManager - Gestione della storia di query apprese dal sistema.
Memorizza coppie (descrizione → query → feedback_qualità) in SQLite.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from difflib import SequenceMatcher
from utils.logging_config import get_logger


logger = get_logger("query_history_manager")


class QueryHistoryManager:
    """Gestisce la memorizzazione e il recupero della storia di query"""
    
    DB_PATH = Path("data") / "query_history.db"
    
    def __init__(self, db_path: str | Path | None = None):
        """Inizializza il database se non esiste"""
        self.DB_PATH = Path(db_path) if db_path else self.DB_PATH
        # Crea cartella data se non esiste
        self.DB_PATH.parent.mkdir(exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Crea le tabelle se non esistono"""
        try:
            with sqlite3.connect(self.DB_PATH) as conn:
                cursor = conn.cursor()
                
                # Tabella per memorizzare query e descrizioni
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS query_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        description TEXT NOT NULL,
                        query_text TEXT NOT NULL,
                        source_type TEXT NOT NULL,
                        feedback_score REAL DEFAULT 0.0,
                        execution_count INTEGER DEFAULT 1,
                        success_count INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_used TIMESTAMP,
                        notes TEXT
                    )
                """)
                
                # Indice sulla descrizione per ricerche rapide
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_description 
                    ON query_history(description)
                """)
                
                conn.commit()
                logger.info("Database query_history inizializzato")
        except Exception as e:
            logger.error(f"Errore inizializzazione DB: {e}")
            raise
    
    def add_query(
        self,
        description: str,
        query_text: str,
        source_type: str = "oracle",
        notes: str = ""
    ) -> int:
        """
        Aggiunge una nuova query alla history.
        Ritorna l'ID della query inserita.
        """
        try:
            with sqlite3.connect(self.DB_PATH) as conn:
                cursor = conn.cursor()
                now = datetime.now().isoformat()
                cursor.execute("""
                    INSERT INTO query_history 
                    (description, query_text, source_type, notes, created_at, last_used)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (description, query_text, source_type, notes, now, now))
                conn.commit()
                query_id = cursor.lastrowid
                logger.info(f"Query aggiunta con ID {query_id}")
                return query_id
        except Exception as e:
            logger.error(f"Errore inserimento query: {e}")
            raise
    
    def find_similar_queries(
        self,
        description: str,
        source_type: str = "oracle",
        similarity_threshold: float = 0.6
    ) -> List[Dict]:
        """
        Trova query simili basate sulla descrizione.
        Usa Levenshtein-like similarity per evitare costi OpenAI.
        Ritorna lista di query ordinate per somiglianza.
        """
        try:
            with sqlite3.connect(self.DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, description, query_text, feedback_score, success_count, execution_count
                    FROM query_history
                    WHERE source_type = ?
                    ORDER BY feedback_score DESC, execution_count DESC
                """, (source_type,))
                
                all_queries = cursor.fetchall()
                
                # Calcola similarità per ogni query storica
                similar = []
                for row in all_queries:
                    qid, desc, query, score, successes, exec_count = row
                    similarity = self._compute_similarity(description, desc)
                    
                    if similarity >= similarity_threshold:
                        similar.append({
                            'id': qid,
                            'description': desc,
                            'query': query,
                            'similarity': similarity,
                            'feedback_score': score,
                            'success_count': successes,
                            'execution_count': exec_count
                        })
                
                # Ordina per similarità (decrescente)
                similar.sort(key=lambda x: x['similarity'], reverse=True)
                logger.info(f"Trovate {len(similar)} query simili per: {description[:40]}")
                return similar
        except Exception as e:
            logger.error(f"Errore ricerca query: {e}")
            return []
    
    def update_feedback(
        self,
        query_id: int,
        success: bool,
        feedback_score: float = None
    ):
        """
        Aggiorna il feedback di una query dopo esecuzione.
        success: True se la query ha dato buoni risultati
        feedback_score: score manuale da 0 a 1
        """
        try:
            with sqlite3.connect(self.DB_PATH) as conn:
                cursor = conn.cursor()
                
                # Ottieni dati attuali
                cursor.execute("""
                    SELECT execution_count, success_count, feedback_score
                    FROM query_history WHERE id = ?
                """, (query_id,))
                
                result = cursor.fetchone()
                if result:
                    exec_count, succ_count, current_score = result
                    
                    # Aggiorna contatori
                    new_exec_count = exec_count + 1
                    new_succ_count = succ_count + (1 if success else 0)
                    success_rate = new_succ_count / new_exec_count if new_exec_count > 0 else 0
                    
                    # Usa feedback_score se fornito, altrimenti usa success_rate
                    final_score = feedback_score if feedback_score is not None else success_rate
                    
                    cursor.execute("""
                        UPDATE query_history
                        SET execution_count = ?,
                            success_count = ?,
                            feedback_score = ?,
                            last_used = ?
                        WHERE id = ?
                    """, (new_exec_count, new_succ_count, final_score, datetime.now().isoformat(), query_id))
                    
                    conn.commit()
                    logger.info(f"Feedback aggiornato per query {query_id}: success={success}, score={final_score:.2f}")
        except Exception as e:
            logger.error(f"Errore aggiornamento feedback: {e}")
    
    def get_top_queries(self, source_type: str = "oracle", limit: int = 5) -> List[Dict]:
        """Ritorna le query con feedback score migliore"""
        try:
            with sqlite3.connect(self.DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, description, query_text, feedback_score, success_count, execution_count
                    FROM query_history
                    WHERE source_type = ?
                    ORDER BY feedback_score DESC, execution_count DESC
                    LIMIT ?
                """, (source_type, limit))
                
                rows = cursor.fetchall()
                return [
                    {
                        'id': row[0],
                        'description': row[1],
                        'query': row[2],
                        'feedback_score': row[3],
                        'success_count': row[4],
                        'execution_count': row[5]
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Errore recupero top queries: {e}")
            return []
    
    def clear_history(self):
        """Pulisce la history (solo per testing)"""
        try:
            with sqlite3.connect(self.DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM query_history")
                conn.commit()
                logger.warning("Query history cancellata")
        except Exception as e:
            logger.error(f"Errore pulizia history: {e}")
    
    @staticmethod
    def _compute_similarity(str1: str, str2: str) -> float:
        """
        Calcola similarità tra due stringhe usando SequenceMatcher.
        Ritorna valore tra 0 e 1.
        """
        # Normalizza (lowercase, spazi)
        s1 = str1.lower().strip()
        s2 = str2.lower().strip()
        
        matcher = SequenceMatcher(None, s1, s2)
        return matcher.ratio()
