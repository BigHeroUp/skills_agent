"""
Learning Monitor - Visualizza e traccia l'apprendimento del sistema
Mostra statistiche su query imparate, feedback scores, e pattern riconosciuti
"""

import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from utils.logging_config import get_logger


logger = get_logger("learning_monitor")


class LearningMonitor:
    """Monitora e visualizza l'apprendimento del sistema"""
    
    def __init__(self, db_path: Path = Path("data") / "query_history.db"):
        self.db_path = db_path
    
    def get_learning_stats(self) -> Dict[str, Any]:
        """
        Ritorna statistiche complete sull'apprendimento del sistema
        
        Returns:
            Dict con:
            - total_queries: N query memorizzate
            - avg_feedback: Score medio
            - best_queries: Query con score più alto
            - query_by_source: Query divise per fonte
            - learning_trend: Trend apprendimento negli ultimi giorni
            - success_rate: % di query reusate con successo
        """
        if not self.db_path.exists():
            return {
                "total_queries": 0,
                "status": "❌ Nessun dato di apprendimento ancora",
                "message": "Sistema non ha ancora memorizzato alcuna query"
            }
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Statistiche generali
                cursor.execute("SELECT COUNT(*) as count FROM query_history")
                total_queries = cursor.fetchone()['count']
                
                if total_queries == 0:
                    return {
                        "total_queries": 0,
                        "status": "⏳ Sistema in learning",
                        "message": "Nessuna query memorizzata ancora"
                    }
                
                # Feedback medio
                cursor.execute("""
                    SELECT 
                        AVG(feedback_score) as avg_feedback,
                        MAX(feedback_score) as max_feedback,
                        MIN(feedback_score) as min_feedback
                    FROM query_history
                """)
                feedback = cursor.fetchone()
                
                # Query per source
                cursor.execute("""
                    SELECT source_type, COUNT(*) as count, AVG(feedback_score) as avg_score
                    FROM query_history
                    GROUP BY source_type
                """)
                by_source = {row['source_type']: {'count': row['count'], 'avg_score': row['avg_score']} for row in cursor.fetchall()}
                
                # Migliori query
                cursor.execute("""
                    SELECT id, description, query_text, feedback_score, execution_count, success_count
                    FROM query_history
                    ORDER BY feedback_score DESC
                    LIMIT 5
                """)
                best_queries = [dict(row) for row in cursor.fetchall()]
                
                # Query riusate
                cursor.execute("""
                    SELECT 
                        SUM(execution_count) as total_executions,
                        SUM(success_count) as total_successes
                    FROM query_history
                """)
                reuse = cursor.fetchone()
                
                total_executions = reuse['total_executions'] or 0
                total_successes = reuse['total_successes'] or 0
                success_rate = (total_successes / total_executions * 100) if total_executions > 0 else 0
                
                # Trend negli ultimi 7 giorni
                cursor.execute("""
                    SELECT 
                        DATE(created_at) as day,
                        COUNT(*) as queries,
                        AVG(feedback_score) as avg_score
                    FROM query_history
                    WHERE created_at >= datetime('now', '-7 days')
                    GROUP BY DATE(created_at)
                    ORDER BY day
                """)
                trend = [dict(row) for row in cursor.fetchall()]
                
                return {
                    "total_queries": total_queries,
                    "avg_feedback": round(feedback['avg_feedback'] or 0, 2),
                    "max_feedback": round(feedback['max_feedback'] or 0, 2),
                    "queries_by_source": by_source,
                    "best_queries": best_queries,
                    "total_executions": total_executions,
                    "success_rate": round(success_rate, 1),
                    "learning_trend": trend,
                    "status": "✅ Sistema Learning Attivo" if total_queries > 0 else "⏳ In Learning"
                }
        
        except Exception as e:
            logger.error(f"Errore lettura stats: {e}")
            return {
                "status": "❌ Errore",
                "message": str(e)
            }
    
    def get_learned_patterns(self) -> Dict[str, List[str]]:
        """
        Estrae pattern comuni dalle query memorizzate
        Es: "trend", "top N", "distribuzione", ecc.
        """
        if not self.db_path.exists():
            return {}
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT description FROM query_history WHERE feedback_score > 0.5")
                descriptions = [row[0] for row in cursor.fetchall()]
                
                # Estrae pattern da descrizioni
                patterns = {}
                for desc in descriptions:
                    keywords = desc.lower().split()
                    for keyword in keywords:
                        if len(keyword) > 3:  # Solo parole significative
                            patterns[keyword] = patterns.get(keyword, 0) + 1
                
                # Ordina per frequenza
                sorted_patterns = dict(sorted(
                    patterns.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10])
                
                return sorted_patterns
        
        except Exception as e:
            logger.error(f"Errore estrazione pattern: {e}")
            return {}
    
    def get_learning_summary(self) -> str:
        """Ritorna un riepilogo leggibile dell'apprendimento"""
        stats = self.get_learning_stats()
        
        if stats.get('total_queries', 0) == 0:
            return """
╔══════════════════════════════════════╗
║  📊 LEARNING STATUS                  ║
╚══════════════════════════════════════╝

⏳ Sistema in fase iniziale di apprendimento

Il sistema memorizza query e i loro risultati per imparare
dai successi precedenti. Completa più analisi per iniziare
il processo di apprendimento automatico.

Come funziona:
1. Esegui analisi dati
2. Sistema memorizza query e feedback
3. Prossime analisi simili riutilizzano query di successo
4. Sistema apprende da cosa funziona meglio
            """
        
        summary = f"""
╔══════════════════════════════════════╗
║  ✅ SISTEMA IN APPRENDIMENTO ATTIVO  ║
╚══════════════════════════════════════╝

📊 STATISTICHE GLOBALI:
  • Query Memorizzate: {stats.get('total_queries', 0)}
  • Score Medio: {stats.get('avg_feedback', 0):.2f}/1.0
  • Query Riusate: {stats.get('total_executions', 0)} volte
  • Success Rate: {stats.get('success_rate', 0)}%

🏆 MIGLIORI QUERY:
"""
        for i, q in enumerate(stats.get('best_queries', [])[:3], 1):
            summary += f"  {i}. {q['description'][:50]}... (score: {q['feedback_score']:.2f})\n"
        
        summary += f"\n📦 QUERY PER FONTE:\n"
        for source, data in stats.get('queries_by_source', {}).items():
            summary += f"  • {source}: {data['count']} query (avg score: {data['avg_score']:.2f})\n"
        
        summary += f"\n📈 COSA IMPARA:\n"
        patterns = self.get_learned_patterns()
        if patterns:
            for i, (pattern, count) in enumerate(list(patterns.items())[:5], 1):
                summary += f"  {i}. {pattern} ({count} volte)\n"
        
        summary += """
🔄 COME FUNZIONA L'APPRENDIMENTO:
  1. Ogni query completata viene memorizzata
  2. I risultati di successo ottengono score alto
  3. Query simili vengono riconosciute e riusate
  4. Il sistema suggerisce query che hanno funzionato prima
  5. Score migliora man mano che il sistema impara

✨ EFFETTO PRATICO:
  • Più analisi fai → Più il sistema impara
  • Query simili → Sistema le riconosce e le riusa
  • Tempo di elaborazione → Diminuisce (meno LLM calls)
  • Qualità risultati → Aumenta (usa le best practices)
        """
        
        return summary
    
    def export_learning_data(self, output_path: str = "data/learning_report.txt") -> bool:
        """Esporta un report completo dell'apprendimento"""
        try:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(self.get_learning_summary())
            
            logger.info(f"Report apprendimento esportato: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Errore export report: {e}")
            return False
    
    def get_dashboard_widget(self) -> Dict[str, Any]:
        """
        Ritorna dati formattati per widget dashboard
        Mostra in tempo reale l'apprendimento del sistema
        """
        stats = self.get_learning_stats()
        
        if stats.get('total_queries', 0) == 0:
            return {
                "title": "🧠 Sistema Learning",
                "status": "⏳ In Inizializzazione",
                "metrics": [
                    {"label": "Query Memorizzate", "value": "0", "icon": "📦"},
                    {"label": "Status", "value": "Completare prima analisi", "icon": "⏳"}
                ]
            }
        
        metrics = [
            {"label": "Query Memorizzate", "value": str(stats.get('total_queries', 0)), "icon": "📦"},
            {"label": "Score Medio", "value": f"{stats.get('avg_feedback', 0):.2f}", "icon": "⭐"},
            {"label": "Riutilizzate", "value": f"{stats.get('success_rate', 0):.0f}%", "icon": "♻️"},
            {"label": "Best Score", "value": f"{stats.get('max_feedback', 0):.2f}", "icon": "🏆"}
        ]
        
        return {
            "title": "🧠 Sistema Learning Attivo",
            "status": "✅ Learning",
            "metrics": metrics,
            "best_queries_count": len(stats.get('best_queries', [])),
            "progress": min(stats.get('total_queries', 0) / 10 * 100, 100)  # 10 query = 100%
        }
