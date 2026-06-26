"""Gestione locale e deterministica delle sessioni di analisi."""

from __future__ import annotations

import copy
import math
import re
import threading
import uuid
from collections import Counter
from datetime import date, datetime
from typing import Any, Callable

from services.analytical_reasoning_layer import AnalyticalReasoningLayer
from services.learning_engine import LearningEngine
from services.pattern_knowledge_engine import PatternKnowledgeEngine


class AnalysisSessionManager:
    """Memorizza richieste e iterazioni analitiche nel processo Python.

    La struttura dei record e intenzionalmente composta da dizionari
    JSON-serializzabili, cosi da poter sostituire in futuro lo storage in
    memoria con un repository SQLite senza cambiare l'API pubblica.
    """

    SCHEMA_VERSION = 1

    def __init__(
        self,
        id_factory: Callable[[], str] | None = None,
        clock: Callable[[], datetime] | None = None,
        knowledge_engine: PatternKnowledgeEngine | None = None,
        learning_engine: LearningEngine | None = None,
        reasoning_layer: AnalyticalReasoningLayer | None = None,
    ):
        self._sessions: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._id_factory = id_factory or (lambda: str(uuid.uuid4()))
        self._clock = clock or datetime.now
        self._learning_engine = learning_engine or LearningEngine(clock=self._clock)
        self._knowledge_engine = knowledge_engine or PatternKnowledgeEngine()
        self._reasoning_layer = reasoning_layer or AnalyticalReasoningLayer()

    def start_session(
        self,
        user_request: str,
        source_type: str,
        dataframe_metadata: dict,
    ) -> dict:
        """Crea una sessione vuota e ne restituisce una copia."""
        session_id = self._id_factory()
        timestamp = self._timestamp()
        session = {
            "schema_version": self.SCHEMA_VERSION,
            "session_id": session_id,
            "created_at": timestamp,
            "updated_at": timestamp,
            "status": "active",
            "user_request": str(user_request or "").strip(),
            "source_type": str(source_type or "unknown").strip().lower(),
            "dataframe_metadata": self._json_safe(dataframe_metadata or {}),
            "iteration_count": 0,
            "iterations": [],
        }
        with self._lock:
            self._sessions[session_id] = session
        return copy.deepcopy(session)

    def add_iteration(
        self,
        session_id: str,
        user_prompt: str,
        analysis_payload: dict,
    ) -> dict:
        """Aggiunge uno snapshot immutabile dei risultati di una iterazione."""
        payload = analysis_payload if isinstance(analysis_payload, dict) else {}
        with self._lock:
            session = self._require_session(session_id)
            iteration_number = len(session["iterations"]) + 1
            detected_patterns = payload.get("detected_patterns")
            if not isinstance(detected_patterns, list):
                detected_patterns = self._knowledge_engine.detect_patterns(
                    user_prompt,
                    session["dataframe_metadata"],
                )
            learning_events = payload.get("learning_events")
            if not isinstance(learning_events, list):
                learning_events = []
                for pattern in detected_patterns:
                    pattern_id = pattern.get("pattern_id") if isinstance(pattern, dict) else None
                    if not pattern_id:
                        continue
                    learning_result = self._learning_engine.record_usage(
                        pattern_id,
                        {
                            "session_id": session_id,
                            "iteration_number": iteration_number,
                            "user_prompt": user_prompt,
                            "request_type": self._classify_request(user_prompt),
                        },
                    )
                    learning_events.append(learning_result["event"])
            learning_state = payload.get("learning_state")
            if not isinstance(learning_state, dict):
                learning_state = self._learning_engine.export_learning_state()
            analytical_strategy = payload.get("analytical_strategy")
            if not isinstance(analytical_strategy, dict):
                analytical_strategy = self._reasoning_layer.build_strategy(
                    user_request=user_prompt,
                    dataframe_metadata=session["dataframe_metadata"],
                    detected_patterns=detected_patterns,
                    learning_state=learning_state,
                )
            reasoning_trace = payload.get("analytical_reasoning_trace")
            if not isinstance(reasoning_trace, dict):
                reasoning_trace = self._reasoning_layer.export_reasoning_trace(
                    analytical_strategy
                )
            iteration = {
                "iteration_number": iteration_number,
                "timestamp": self._timestamp(),
                "user_prompt": str(user_prompt or "").strip(),
                "request_type": self._classify_request(user_prompt),
                "analysis_plan": self._json_safe(payload.get("analysis_plan") or {}),
                "deterministic_results": self._json_safe(
                    payload.get("deterministic_results") or {}
                ),
                "insights": self._json_safe(payload.get("insights") or {}),
                "detected_patterns": self._json_safe(detected_patterns),
                "learning_events": self._json_safe(learning_events),
                "learning_state": self._json_safe(learning_state),
                "analytical_strategy": self._json_safe(analytical_strategy),
                "analytical_reasoning_trace": self._json_safe(reasoning_trace),
                "anomaly_detection_results": self._json_safe(
                    payload.get("anomaly_detection_results") or {}
                ),
                "root_cause_results": self._json_safe(
                    payload.get("root_cause_results") or {}
                ),
                "final_report_snapshot": str(
                    payload.get("final_report_snapshot")
                    or payload.get("final_report")
                    or ""
                ),
            }
            session["iterations"].append(iteration)
            session["iteration_count"] = iteration_number
            session["updated_at"] = iteration["timestamp"]
            return copy.deepcopy(iteration)

    def get_session(self, session_id: str) -> dict | None:
        """Recupera una copia della sessione oppure ``None`` se non esiste."""
        with self._lock:
            session = self._sessions.get(session_id)
            return copy.deepcopy(session) if session is not None else None

    def build_context_for_next_iteration(self, session_id: str) -> dict:
        """Costruisce il contesto necessario per un follow-up analitico."""
        with self._lock:
            session = self._require_session(session_id)
            iterations = session["iterations"]
            latest = iterations[-1] if iterations else None
            return copy.deepcopy({
                "session_id": session["session_id"],
                "source_type": session["source_type"],
                "dataframe_metadata": session["dataframe_metadata"],
                "original_user_request": session["user_request"],
                "iteration_count": session["iteration_count"],
                "request_history": [
                    {
                        "iteration_number": item["iteration_number"],
                        "user_prompt": item["user_prompt"],
                        "request_type": item["request_type"],
                    }
                    for item in iterations
                ],
                "latest_iteration": latest,
                "latest_analysis_plan": latest["analysis_plan"] if latest else {},
                "latest_deterministic_results": (
                    latest["deterministic_results"] if latest else {}
                ),
                "latest_insights": latest["insights"] if latest else {},
                "latest_detected_patterns": (
                    latest["detected_patterns"] if latest else []
                ),
                "latest_learning_events": latest.get("learning_events", []) if latest else [],
                "latest_learning_state": latest.get("learning_state", {}) if latest else {},
                "latest_analytical_strategy": (
                    latest.get("analytical_strategy", {}) if latest else {}
                ),
                "latest_analytical_reasoning_trace": (
                    latest.get("analytical_reasoning_trace", {}) if latest else {}
                ),
                "latest_anomaly_detection_results": (
                    latest.get("anomaly_detection_results", {}) if latest else {}
                ),
                "latest_root_cause_results": (
                    latest.get("root_cause_results", {}) if latest else {}
                ),
                "latest_final_report": (
                    latest["final_report_snapshot"] if latest else ""
                ),
            })

    def export_session_summary(self, session_id: str) -> dict:
        """Esporta una sintesi JSON-safe della sessione e delle iterazioni."""
        with self._lock:
            session = self._require_session(session_id)
            iterations = session["iterations"]
            request_type_counts = Counter(
                item["request_type"] for item in iterations
            )
            analysis_types = []
            for item in iterations:
                analysis_type = item["analysis_plan"].get("analysis_type")
                if analysis_type and analysis_type not in analysis_types:
                    analysis_types.append(analysis_type)

            return copy.deepcopy({
                "schema_version": session["schema_version"],
                "session_id": session["session_id"],
                "status": session["status"],
                "created_at": session["created_at"],
                "updated_at": session["updated_at"],
                "user_request": session["user_request"],
                "source_type": session["source_type"],
                "dataframe_metadata": session["dataframe_metadata"],
                "iteration_count": session["iteration_count"],
                "request_type_counts": dict(request_type_counts),
                "analysis_types": analysis_types,
                "iteration_summaries": [
                    {
                        "iteration_number": item["iteration_number"],
                        "timestamp": item["timestamp"],
                        "user_prompt": item["user_prompt"],
                        "request_type": item["request_type"],
                        "analysis_type": item["analysis_plan"].get("analysis_type"),
                        "has_results": bool(item["deterministic_results"]),
                        "has_insights": bool(item["insights"]),
                        "detected_pattern_ids": [
                            pattern.get("pattern_id")
                            for pattern in item.get("detected_patterns", [])
                        ],
                        "learning_event_count": len(item.get("learning_events", [])),
                        "strategy_id": (
                            item.get("analytical_strategy", {}).get("strategy_id")
                        ),
                        "clarification_question_count": len(
                            item.get("analytical_strategy", {}).get(
                                "clarification_questions",
                                [],
                            )
                        ),
                        "anomaly_count": item.get(
                            "anomaly_detection_results",
                            {},
                        ).get("anomaly_count", 0),
                        "root_cause_count": item.get(
                            "root_cause_results",
                            {},
                        ).get("root_cause_count", 0),
                        "has_final_report": bool(item["final_report_snapshot"]),
                    }
                    for item in iterations
                ],
                "learning_state": (
                    iterations[-1].get("learning_state", {}) if iterations else {}
                ),
                "latest_analytical_strategy": (
                    iterations[-1].get("analytical_strategy", {}) if iterations else {}
                ),
                "latest_analytical_reasoning_trace": (
                    iterations[-1].get("analytical_reasoning_trace", {})
                    if iterations
                    else {}
                ),
                "latest_anomaly_detection_results": (
                    iterations[-1].get("anomaly_detection_results", {})
                    if iterations
                    else {}
                ),
                "latest_root_cause_results": (
                    iterations[-1].get("root_cause_results", {})
                    if iterations
                    else {}
                ),
                "latest_final_report": (
                    iterations[-1]["final_report_snapshot"] if iterations else ""
                ),
            })

    def _classify_request(self, user_prompt: str) -> str:
        prompt = self._normalize(user_prompt)

        if self._contains_any(prompt, [
            "anomalia",
            "anomalie",
            "anomalo",
            "outlier",
            "valori estremi",
            "picco anomalo",
        ]):
            return "anomaly_deep_dive"

        if self._contains_any(prompt, [
            "soglia",
            "superiore a",
            "inferiore a",
            "maggiore di",
            "minore di",
            "piu di",
            "meno di",
            "uguale a",
            "almeno",
            "oltre ",
            "sotto ",
            "confronta",
            "comparison",
            "threshold",
        ]) or re.search(r"(?:>=|<=|>|<)\s*\d", prompt):
            return "threshold_comparison"

        if self._contains_any(prompt, [
            "periodo",
            "intervallo temporale",
            "finestra temporale",
            "ultimo mese",
            "ultimi mesi",
            "ultima settimana",
            "ultime settimane",
            "ultimo anno",
            "ultimi anni",
            "trimestre",
            "semestre",
            "mensile",
            "settimanale",
            "giornaliero",
            "dal ",
            "dall ",
            "tra gennaio",
            "time window",
        ]):
            return "time_window_request"

        if self._contains_any(prompt, [
            "segmenta",
            "segmentazione",
            "raggruppa",
            "raggruppamento",
            "suddividi",
            "distribuzione per",
            "per categoria",
            "per stato",
            "per cliente",
            "per regione",
            "per canale",
            "group by",
        ]):
            return "segmentation_request"

        if self._contains_any(prompt, [
            "approfondisci",
            "raffina",
            "rielabora",
            "ricalcola",
            "modifica",
            "aggiungi",
            "escludi",
            "filtra",
            "dettaglio",
            "piu dettaglio",
            "correggi",
        ]):
            return "refinement"

        return "initial_analysis"

    def _require_session(self, session_id: str) -> dict[str, Any]:
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(f"Sessione di analisi non trovata: {session_id}")
        return session

    def _timestamp(self) -> str:
        return self._clock().isoformat()

    def _contains_any(self, prompt: str, terms: list[str]) -> bool:
        return any(term in prompt for term in terms)

    def _normalize(self, value: str) -> str:
        return re.sub(r"\s+", " ", str(value or "").lower()).strip()

    def _json_safe(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): self._json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._json_safe(item) for item in value]
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, float) and not math.isfinite(value):
            return None
        if hasattr(value, "item"):
            return self._json_safe(value.item())
        return value
