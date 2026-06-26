"""Motore locale di apprendimento sui pattern analitici."""

from __future__ import annotations

import copy
import json
import math
import re
import threading
import uuid
from collections import Counter
from datetime import date, datetime
from typing import Any, Callable


class LearningEngine:
    """Traccia utilizzi e feedback dei pattern senza chiamate esterne.

    Lo storage e volutamente in memoria e composto da dizionari JSON-safe, cosi
    da poter essere spostato in SQLite mantenendo stabile il contratto pubblico.
    """

    SCHEMA_VERSION = 1
    PROMOTION_THRESHOLD = 0.72
    DEMOTION_THRESHOLD = 0.28

    POSITIVE_FEEDBACK = {
        "utile",
        "positivo",
        "positive",
        "success",
        "successful",
        "ok",
        "yes",
        "si",
        "sì",
        "like",
    }
    NEGATIVE_FEEDBACK = {
        "non utile",
        "inutile",
        "negativo",
        "negative",
        "failure",
        "failed",
        "no",
        "dislike",
    }

    def __init__(
        self,
        initial_state: dict[str, Any] | None = None,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ):
        self._lock = threading.RLock()
        self._clock = clock or datetime.now
        self._id_factory = id_factory or (lambda: str(uuid.uuid4()))
        self._patterns: dict[str, dict[str, Any]] = {}
        self._events: list[dict[str, Any]] = []
        if initial_state:
            self._load_state(initial_state)

    def record_usage(
        self,
        pattern_id: str,
        context: dict | None = None,
    ) -> dict:
        """Registra un utilizzo del pattern e aggiorna il confidence score."""
        pattern_id = self._require_pattern_id(pattern_id)
        with self._lock:
            stats = self._ensure_stats(pattern_id)
            stats["usage_count"] += 1
            stats["last_used_at"] = self._timestamp()
            event = self._event("usage", pattern_id, None, context)
            stats["events"].append(event)
            self._events.append(event)
            updated = self._update_confidence_locked(pattern_id)
            updated["event"] = copy.deepcopy(event)
            return self._json_safe(updated)

    def record_feedback(
        self,
        pattern_id: str,
        feedback: str,
        context: dict | None = None,
    ) -> dict:
        """Registra feedback utente e aggiorna successi, fallimenti e stato."""
        pattern_id = self._require_pattern_id(pattern_id)
        normalized_feedback = self._normalize_feedback(feedback)
        with self._lock:
            stats = self._ensure_stats(pattern_id)
            stats["feedback_count"] += 1
            stats["last_feedback_at"] = self._timestamp()
            if normalized_feedback == "positive":
                stats["success_count"] += 1
            elif normalized_feedback == "negative":
                stats["failure_count"] += 1
            else:
                stats["neutral_count"] += 1

            event = self._event(
                "feedback",
                pattern_id,
                normalized_feedback,
                {
                    **(context or {}),
                    "raw_feedback": str(feedback or ""),
                },
            )
            stats["events"].append(event)
            self._events.append(event)
            updated = self._update_confidence_locked(pattern_id)
            updated["event"] = copy.deepcopy(event)
            return self._json_safe(updated)

    def update_confidence(self, pattern_id: str) -> dict:
        """Ricalcola il confidence score corrente per un pattern."""
        pattern_id = self._require_pattern_id(pattern_id)
        with self._lock:
            self._ensure_stats(pattern_id)
            return self._json_safe(self._update_confidence_locked(pattern_id))

    def get_pattern_stats(self, pattern_id: str) -> dict | None:
        """Restituisce una copia degli indicatori di apprendimento del pattern."""
        pattern_id = self._require_pattern_id(pattern_id)
        with self._lock:
            stats = self._patterns.get(pattern_id)
            return self._json_safe(copy.deepcopy(stats)) if stats else None

    def recommend_patterns(
        self,
        user_request: str,
        available_patterns: list[dict],
    ) -> list[dict]:
        """Ordina i pattern disponibili usando confidence appresa e match locale."""
        request = self._normalize(user_request)
        recommendations = []
        with self._lock:
            for pattern in available_patterns or []:
                if not isinstance(pattern, dict):
                    continue
                pattern_id = pattern.get("pattern_id")
                if not pattern_id:
                    continue
                base_confidence = self._safe_float(
                    pattern.get("confidence_score"),
                    default=0.0,
                )
                stats = self._patterns.get(str(pattern_id))
                learned_confidence = (
                    self._safe_float(stats.get("confidence_score"), base_confidence)
                    if stats
                    else base_confidence
                )
                keyword_score = self._keyword_score(request, pattern)
                recommendation_score = round(
                    min(1.0, learned_confidence * 0.75 + keyword_score * 0.25),
                    4,
                )
                item = copy.deepcopy(pattern)
                item["learning"] = self._public_learning_stats(
                    stats,
                    fallback_confidence=base_confidence,
                )
                item["confidence_score"] = round(learned_confidence, 4)
                item["recommendation_score"] = recommendation_score
                recommendations.append(item)

        recommendations.sort(
            key=lambda item: (
                -item["confidence_score"],
                -item["recommendation_score"],
                item.get("pattern_id", ""),
            )
        )
        return self._json_safe(recommendations)

    def export_learning_state(self) -> dict:
        """Esporta stato e audit trail in formato pronto per persistenza SQLite."""
        with self._lock:
            promoted = [
                pattern_id
                for pattern_id, stats in self._patterns.items()
                if stats["status"] == "promoted"
            ]
            demoted = [
                pattern_id
                for pattern_id, stats in self._patterns.items()
                if stats["status"] == "demoted"
            ]
            confidence_values = [
                stats["confidence_score"] for stats in self._patterns.values()
            ]
            state = {
                "schema_version": self.SCHEMA_VERSION,
                "storage": "memory",
                "pattern_count": len(self._patterns),
                "event_count": len(self._events),
                "promoted_pattern_ids": sorted(promoted),
                "demoted_pattern_ids": sorted(demoted),
                "average_confidence": (
                    round(sum(confidence_values) / len(confidence_values), 4)
                    if confidence_values
                    else 0.0
                ),
                "patterns": [
                    copy.deepcopy(self._patterns[pattern_id])
                    for pattern_id in sorted(self._patterns)
                ],
                "events": copy.deepcopy(self._events),
                "recommendations": self._build_improvement_recommendations(),
                "persistence": {
                    "target": "sqlite",
                    "suggested_tables": [
                        "learning_patterns",
                        "learning_events",
                        "learning_recommendations",
                    ],
                },
            }
            return self._json_safe(state)

    def _ensure_stats(self, pattern_id: str) -> dict[str, Any]:
        if pattern_id not in self._patterns:
            now = self._timestamp()
            self._patterns[pattern_id] = {
                "pattern_id": pattern_id,
                "schema_version": self.SCHEMA_VERSION,
                "usage_count": 0,
                "success_count": 0,
                "failure_count": 0,
                "neutral_count": 0,
                "feedback_count": 0,
                "confidence_score": 0.5,
                "status": "candidate",
                "created_at": now,
                "updated_at": now,
                "last_used_at": None,
                "last_feedback_at": None,
                "events": [],
                "recommendations": [],
            }
        return self._patterns[pattern_id]

    def _update_confidence_locked(self, pattern_id: str) -> dict:
        stats = self._patterns[pattern_id]
        usage_count = int(stats.get("usage_count", 0) or 0)
        success_count = int(stats.get("success_count", 0) or 0)
        failure_count = int(stats.get("failure_count", 0) or 0)
        neutral_count = int(stats.get("neutral_count", 0) or 0)

        total_feedback = success_count + failure_count + neutral_count
        feedback_component = (
            (success_count + 0.5 * neutral_count + 1.0) / (total_feedback + 2.0)
            if total_feedback
            else 0.5
        )
        usage_component = min(0.16, usage_count * 0.02)
        penalty = min(0.24, failure_count * 0.08)
        confidence = max(
            0.0,
            min(1.0, feedback_component * 0.86 + usage_component - penalty),
        )
        stats["confidence_score"] = round(confidence, 4)
        stats["status"] = self._status_for(stats)
        stats["updated_at"] = self._timestamp()
        stats["recommendations"] = self._recommendations_for(stats)
        return copy.deepcopy(stats)

    def _status_for(self, stats: dict[str, Any]) -> str:
        confidence = float(stats.get("confidence_score", 0.0) or 0.0)
        usage_count = int(stats.get("usage_count", 0) or 0)
        success_count = int(stats.get("success_count", 0) or 0)
        failure_count = int(stats.get("failure_count", 0) or 0)
        if (
            confidence >= self.PROMOTION_THRESHOLD
            and usage_count >= 2
            and success_count >= 2
        ):
            return "promoted"
        if confidence <= self.DEMOTION_THRESHOLD or (
            failure_count >= 2 and failure_count > success_count
        ):
            return "demoted"
        return "candidate"

    def _recommendations_for(self, stats: dict[str, Any]) -> list[str]:
        status = stats.get("status")
        confidence = float(stats.get("confidence_score", 0.0) or 0.0)
        usage_count = int(stats.get("usage_count", 0) or 0)
        recommendations = []
        if status == "promoted":
            recommendations.append(
                "Promuovere il pattern nel ranking e riusarlo come best practice locale."
            )
        elif status == "demoted":
            recommendations.append(
                "Declassare il pattern e richiedere evidenze aggiuntive prima del riuso automatico."
            )
        elif usage_count < 2:
            recommendations.append(
                "Raccogliere ulteriori utilizzi prima di consolidare il pattern."
            )
        elif confidence < 0.5:
            recommendations.append(
                "Rivedere metriche, segmentazioni o trigger associati al pattern."
            )
        else:
            recommendations.append(
                "Continuare a raccogliere feedback per stabilizzare il confidence score."
            )
        return recommendations

    def _build_improvement_recommendations(self) -> list[dict[str, Any]]:
        output = []
        for pattern_id, stats in sorted(self._patterns.items()):
            for recommendation in stats.get("recommendations", []):
                output.append({
                    "pattern_id": pattern_id,
                    "status": stats.get("status"),
                    "confidence_score": stats.get("confidence_score"),
                    "recommendation": recommendation,
                })
        return output

    def _event(
        self,
        event_type: str,
        pattern_id: str,
        feedback: str | None,
        context: dict | None,
    ) -> dict[str, Any]:
        event = {
            "event_id": self._id_factory(),
            "schema_version": self.SCHEMA_VERSION,
            "event_type": event_type,
            "pattern_id": pattern_id,
            "feedback": feedback,
            "timestamp": self._timestamp(),
            "context": self._json_safe(context or {}),
        }
        return self._json_safe(event)

    def _load_state(self, state: dict[str, Any]) -> None:
        patterns = state.get("patterns", []) if isinstance(state, dict) else []
        for pattern in patterns:
            if isinstance(pattern, dict) and pattern.get("pattern_id"):
                self._patterns[str(pattern["pattern_id"])] = self._json_safe(pattern)
        events = state.get("events", []) if isinstance(state, dict) else []
        self._events = [
            self._json_safe(event)
            for event in events
            if isinstance(event, dict)
        ]

    def _public_learning_stats(
        self,
        stats: dict[str, Any] | None,
        fallback_confidence: float,
    ) -> dict[str, Any]:
        if not stats:
            return {
                "usage_count": 0,
                "success_count": 0,
                "failure_count": 0,
                "feedback_count": 0,
                "confidence_score": round(fallback_confidence, 4),
                "status": "unseen",
                "recommendations": [
                    "Pattern non ancora osservato dal Learning Engine."
                ],
            }
        return {
            "usage_count": stats.get("usage_count", 0),
            "success_count": stats.get("success_count", 0),
            "failure_count": stats.get("failure_count", 0),
            "feedback_count": stats.get("feedback_count", 0),
            "confidence_score": stats.get("confidence_score", fallback_confidence),
            "status": stats.get("status", "candidate"),
            "recommendations": stats.get("recommendations", []),
        }

    def _keyword_score(self, request: str, pattern: dict[str, Any]) -> float:
        keywords = pattern.get("trigger_keywords", []) or []
        if not request or not keywords:
            return 0.0
        matches = 0
        for keyword in keywords:
            normalized = self._normalize(keyword)
            if not normalized:
                continue
            if " " in normalized and normalized in request:
                matches += 1
            elif re.search(rf"\b{re.escape(normalized)}\w*\b", request):
                matches += 1
        return min(1.0, matches / 4)

    def _normalize_feedback(self, feedback: str) -> str:
        value = self._normalize(feedback)
        if value in self.POSITIVE_FEEDBACK:
            return "positive"
        if value in self.NEGATIVE_FEEDBACK:
            return "negative"
        return "neutral"

    def _require_pattern_id(self, pattern_id: str) -> str:
        normalized = str(pattern_id or "").strip()
        if not normalized:
            raise ValueError("pattern_id obbligatorio")
        return normalized

    def _timestamp(self) -> str:
        return self._clock().isoformat()

    def _normalize(self, value: Any) -> str:
        return re.sub(r"\s+", " ", str(value or "").lower()).strip()

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            result = float(value)
        except (TypeError, ValueError):
            return default
        return result if math.isfinite(result) else default

    def _json_safe(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): self._json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._json_safe(item) for item in value]
        if isinstance(value, Counter):
            return dict(value)
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, float) and not math.isfinite(value):
            return None
        if hasattr(value, "item"):
            return self._json_safe(value.item())
        json.dumps(value, ensure_ascii=False, default=str)
        return value
