"""Kernel capability for deterministic Knowledge Graph queries."""

from __future__ import annotations

from pathlib import Path

from core.kernel.capability import Capability, CapabilityRequest, CapabilityResponse
from services.knowledge_graph.query_engine import KnowledgeGraphQueryEngine
from services.knowledge_graph.store import KnowledgeGraphStore


class KnowledgeGraphQueryCapability(Capability):
    """Execute deterministic user questions against the local Knowledge Graph."""

    name = "knowledge_graph.query"
    version = "1.0.0"
    description = (
        "Answer deterministic questions against the local Knowledge Graph JSON "
        "without using external LLM services"
    )

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else KnowledgeGraphStore.DEFAULT_PATH

    def execute(self, request: CapabilityRequest) -> CapabilityResponse:
        payload = request.payload if isinstance(request.payload, dict) else {}
        question = str(payload.get("question", "") or "").strip()
        mode = str(payload.get("mode", "deterministic") or "").strip().lower()

        if not question:
            return CapabilityResponse(
                success=False,
                errors=["Il payload deve includere una domanda non vuota nel campo 'question'."],
                metadata={
                    "error_type": "ValidationError",
                    "graph_path": str(self.path),
                },
            )

        if mode != "deterministic":
            return CapabilityResponse(
                success=False,
                errors=["La capability supporta solo mode='deterministic'."],
                metadata={
                    "error_type": "ValidationError",
                    "graph_path": str(self.path),
                    "mode": mode,
                },
            )

        engine = KnowledgeGraphQueryEngine(path=self.path)
        result = engine.answer_question_deterministic(question)

        return CapabilityResponse(
            success=True,
            result={
                "question": result.get("question", question),
                "answer": result.get("answer", ""),
                "matches": list(result.get("matches") or []),
                "confidence": float(result.get("confidence", 0.0) or 0.0),
                "execution_type": result.get(
                    "execution_type",
                    "deterministic_kg_query",
                ),
            },
            metadata={
                "graph_path": str(self.path),
                "mode": mode,
            },
        )
