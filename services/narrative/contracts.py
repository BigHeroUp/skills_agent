"""Contracts for optional non-critical narrative enrichment."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

from services.knowledge_graph.domain.issues import freeze_json, json_safe


class NarrativePurpose(str, Enum):
    EXECUTIVE_SUMMARY = "executive_summary"
    PROFESSIONAL_REWRITE = "professional_rewrite"
    NATURAL_EXPLANATION = "natural_explanation"


@dataclass(frozen=True)
class NarrativeRequest:
    purpose: NarrativePurpose
    deterministic_text: str
    facts: Mapping[str, Any] = field(default_factory=dict)
    audience: str = "business"
    language: str = "it"
    critical: bool = False

    def __post_init__(self) -> None:
        if not self.deterministic_text.strip():
            raise ValueError("deterministic_text must be non-empty")
        object.__setattr__(self, "facts", freeze_json(self.facts))


@dataclass(frozen=True)
class NarrativeResult:
    status: str
    content: str
    deterministic_text: str
    purpose: NarrativePurpose
    used_llm: bool
    model: str | None
    error: str | None
    provenance: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "provenance", MappingProxyType(dict(self.provenance)))

    def to_dict(self) -> dict[str, Any]:
        return json_safe({
            "content": self.content,
            "deterministic_text": self.deterministic_text,
            "error": self.error,
            "model": self.model,
            "provenance": self.provenance,
            "purpose": self.purpose.value,
            "status": self.status,
            "used_llm": self.used_llm,
        })
