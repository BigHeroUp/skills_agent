"""Data models for deterministic analytical experience."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class AnalyticalExperience:
    """Reusable analytical knowledge derived from one or more analysis runs."""

    id: str
    title: str
    description: str
    source_analysis_run_ids: list[str] = field(default_factory=list)
    metrics: list[str] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)
    anomalies: list[str] = field(default_factory=list)
    root_causes: list[str] = field(default_factory=list)
    recommended_steps: list[str] = field(default_factory=list)
    confidence: float = 0.0
    evidence_count: int = 0
    created_at: str = ""
    updated_at: str = ""
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AnalyticalExperience":
        return cls(
            id=str(payload.get("id", "")),
            title=str(payload.get("title", "")),
            description=str(payload.get("description", "")),
            source_analysis_run_ids=[str(item) for item in payload.get("source_analysis_run_ids", []) or []],
            metrics=[str(item) for item in payload.get("metrics", []) or []],
            columns=[str(item) for item in payload.get("columns", []) or []],
            anomalies=[str(item) for item in payload.get("anomalies", []) or []],
            root_causes=[str(item) for item in payload.get("root_causes", []) or []],
            recommended_steps=[str(item) for item in payload.get("recommended_steps", []) or []],
            confidence=float(payload.get("confidence", 0.0) or 0.0),
            evidence_count=int(payload.get("evidence_count", 0) or 0),
            created_at=str(payload.get("created_at", "")),
            updated_at=str(payload.get("updated_at", "")),
            tags=[str(item) for item in payload.get("tags", []) or []],
        )


@dataclass
class ExperiencePattern:
    """Recurring pattern extracted from multiple analytical experiences."""

    id: str
    pattern_type: str
    label: str
    frequency: int
    confidence: float
    evidence_ids: list[str] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExperienceRecommendation:
    """Recommendation produced from accumulated deterministic experience."""

    step: str
    reason: str
    priority: str
    confidence: float
    source_experience_ids: list[str] = field(default_factory=list)
