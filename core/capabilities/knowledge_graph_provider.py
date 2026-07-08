"""Provider for Knowledge Graph related kernel capabilities."""

from __future__ import annotations

from pathlib import Path

from core.kernel.provider import CapabilityProvider

from .knowledge_graph_query import KnowledgeGraphQueryCapability


class KnowledgeGraphCapabilityProvider(CapabilityProvider):
    """Register Knowledge Graph kernel capabilities."""

    name = "knowledge_graph_provider"
    version = "1.0.0"
    description = "Provides deterministic Knowledge Graph capabilities"

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = path

    def list_capabilities(self) -> list[KnowledgeGraphQueryCapability]:
        return [KnowledgeGraphQueryCapability(path=self.path)]
