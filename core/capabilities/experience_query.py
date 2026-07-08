"""Kernel capability for deterministic experience queries."""

from __future__ import annotations

from pathlib import Path

from core.kernel.capability import Capability, CapabilityRequest, CapabilityResponse
from services.experience.experience_engine import AnalyticalExperienceEngine
from services.experience.experience_query import query_experience
from services.experience.experience_store import ExperienceStore
from services.knowledge_graph.store import KnowledgeGraphStore


class ExperienceQueryCapability(Capability):
    """Answer deterministic questions over the analytical experience store."""

    name = "experience.query"
    version = "1.0.0"
    description = "Query deterministic analytical experience without OpenAI"
    category = "experience"
    tags = ["experience", "memory", "recommendation", "deterministic", "offline"]
    deterministic = True
    offline = True
    experimental = True
    owner = "experience-platform"

    def __init__(
        self,
        kg_path: str | Path | None = None,
        experience_path: str | Path | None = None,
    ) -> None:
        self.kg_path = Path(kg_path) if kg_path is not None else KnowledgeGraphStore.DEFAULT_PATH
        self.experience_path = (
            Path(experience_path) if experience_path is not None else ExperienceStore.DEFAULT_PATH
        )

    def execute(self, request: CapabilityRequest) -> CapabilityResponse:
        payload = request.payload if isinstance(request.payload, dict) else {}
        question = str(payload.get("question", "") or "").strip()
        mode = str(payload.get("mode", "deterministic") or "").strip().lower()

        if not question:
            return CapabilityResponse(
                success=False,
                errors=["Il payload deve includere una domanda non vuota nel campo 'question'."],
                metadata={"error_type": "ValidationError"},
            )

        if mode != "deterministic":
            return CapabilityResponse(
                success=False,
                errors=["La capability supporta solo mode='deterministic'."],
                metadata={"error_type": "ValidationError", "mode": mode},
            )

        engine = AnalyticalExperienceEngine(
            experience_path=self.experience_path,
            kg_path=self.kg_path,
        )
        result = query_experience(question, engine=engine, limit=5)

        return CapabilityResponse(
            success=bool(result.get("success", True)),
            result={
                "question": result.get("question", question),
                "answer": result.get("answer", ""),
                "matches": list(result.get("matches") or []),
                "recommendations": list(result.get("recommendations") or []),
                "confidence": float(result.get("confidence", 0.0) or 0.0),
                "execution_type": result.get("execution_type", "deterministic_experience_query"),
            },
            errors=[] if result.get("success", True) else [result.get("answer", "Errore query esperienza")],
            metadata={
                "kg_path": str(self.kg_path),
                "experience_path": str(self.experience_path),
                "mode": mode,
                "category": self.category,
                "tags": list(self.tags),
                "deterministic": self.deterministic,
                "offline": self.offline,
                "experimental": self.experimental,
                "owner": self.owner,
            },
        )
