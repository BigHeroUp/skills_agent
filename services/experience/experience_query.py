"""Deterministic query layer over the analytical experience store."""

from __future__ import annotations

import re
from typing import Any

from .experience_engine import AnalyticalExperienceEngine


STOPWORDS = {
    "casi",
    "simili",
    "cosa",
    "abbiamo",
    "imparato",
    "dall",
    "esperienza",
    "esperienze",
    "pattern",
    "ricorrenti",
    "raccomandazioni",
    "metriche",
    "root",
    "cause",
    "anomalie",
    "sui",
    "sul",
    "sulla",
    "di",
    "su",
    "le",
    "gli",
    "il",
    "la",
    "i",
}


def query_experience(
    question: str,
    engine: AnalyticalExperienceEngine | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    """Answer deterministic questions over accumulated analytical experience."""

    clean_question = str(question or "").strip()
    if not clean_question:
        return {
            "success": False,
            "question": clean_question,
            "answer": "La query esperienza richiede una domanda non vuota.",
            "matches": [],
            "recommendations": [],
            "confidence": 0.0,
            "execution_type": "deterministic_experience_query",
        }

    resolved_engine = engine or AnalyticalExperienceEngine()
    if not resolved_engine.experience_store.list_experiences():
        resolved_engine.refresh_experience_from_kg(limit=20)

    summary = resolved_engine.get_experience_summary()
    if summary.get("total_experiences", 0) == 0:
        return {
            "success": True,
            "question": clean_question,
            "answer": "Non ci sono ancora esperienze analitiche sufficienti. Esegui prima il refresh dell'experience store.",
            "matches": [],
            "recommendations": [],
            "confidence": 0.0,
            "execution_type": "deterministic_experience_query",
        }

    lowered = clean_question.lower()
    profile = _profile_from_question(clean_question)

    if "raccomandazioni dall'esperienza" in lowered:
        recommendations = resolved_engine.recommend_from_experience(profile, limit=limit)
        items = recommendations.get("recommendations", [])
        answer = (
            "Raccomandazioni dall'esperienza: "
            + "; ".join(item["step"] for item in items[:3])
            if items
            else "Non ci sono raccomandazioni rilevanti dall'esperienza disponibile."
        )
        return {
            "success": True,
            "question": clean_question,
            "answer": answer,
            "matches": [],
            "recommendations": items,
            "confidence": items[0]["confidence"] if items else 0.2,
            "execution_type": "deterministic_experience_query",
        }

    if "metriche ricorrenti" in lowered:
        metrics = summary.get("top_metrics", [])
        return {
            "success": True,
            "question": clean_question,
            "answer": (
                "Metriche ricorrenti: " + ", ".join(metrics[:5])
                if metrics
                else "Non sono state trovate metriche ricorrenti."
            ),
            "matches": metrics,
            "recommendations": [],
            "confidence": 0.72 if metrics else 0.2,
            "execution_type": "deterministic_experience_query",
        }

    if "root cause ricorrenti" in lowered:
        root_causes = summary.get("top_root_causes", [])
        return {
            "success": True,
            "question": clean_question,
            "answer": (
                "Root cause ricorrenti: " + ", ".join(root_causes[:5])
                if root_causes
                else "Non sono state trovate root cause ricorrenti."
            ),
            "matches": root_causes,
            "recommendations": [],
            "confidence": 0.72 if root_causes else 0.2,
            "execution_type": "deterministic_experience_query",
        }

    if "anomalie ricorrenti" in lowered:
        anomalies = summary.get("top_anomalies", [])
        return {
            "success": True,
            "question": clean_question,
            "answer": (
                "Anomalie ricorrenti: " + ", ".join(anomalies[:5])
                if anomalies
                else "Non sono state trovate anomalie ricorrenti."
            ),
            "matches": anomalies,
            "recommendations": [],
            "confidence": 0.72 if anomalies else 0.2,
            "execution_type": "deterministic_experience_query",
        }

    if any(
        phrase in lowered
        for phrase in (
            "esperienze",
            "casi simili",
            "cosa abbiamo imparato",
            "pattern ricorrenti",
        )
    ):
        relevant = resolved_engine.find_relevant_experiences(profile, limit=limit)
        matches = relevant.get("experiences", [])
        recommendations = resolved_engine.recommend_from_experience(profile, limit=limit).get("recommendations", [])
        if matches:
            answer = (
                f"Ho trovato {len(matches)} esperienze rilevanti. "
                f"Le più utili riguardano: {', '.join(item['title'] for item in matches[:2])}."
            )
        else:
            answer = (
                "Non ho trovato casi sufficientemente simili, ma l'experience store contiene "
                f"{summary.get('total_experiences', 0)} esperienze aggregate."
            )
        return {
            "success": True,
            "question": clean_question,
            "answer": answer,
            "matches": matches,
            "recommendations": recommendations,
            "confidence": matches[0]["score"] if matches else 0.25,
            "execution_type": "deterministic_experience_query",
        }

    return {
        "success": True,
        "question": clean_question,
        "answer": (
            "La query esperienza supporta domande su esperienze, casi simili, cosa abbiamo imparato, "
            "pattern ricorrenti, metriche ricorrenti, anomalie ricorrenti, root cause ricorrenti "
            "e raccomandazioni dall'esperienza."
        ),
        "matches": [],
        "recommendations": [],
        "confidence": 0.1,
        "execution_type": "deterministic_experience_query",
    }


def _profile_from_question(question: str) -> dict[str, Any]:
    tokens = [
        token
        for token in re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", str(question or "").lower())
        if token not in STOPWORDS
    ]
    return {
        "metrics": tokens,
        "columns": tokens,
        "anomalies": tokens,
        "root_causes": tokens,
        "tags": tokens,
    }
