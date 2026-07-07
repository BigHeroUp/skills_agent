"""Modelli leggeri per il Knowledge Graph interno."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class KnowledgeNode:
    """Nodo generico del grafo."""

    id: str
    type: str
    label: str
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "KnowledgeNode":
        return cls(
            id=str(payload.get("id", "")),
            type=str(payload.get("type", "")),
            label=str(payload.get("label", "")),
            properties=dict(payload.get("properties") or {}),
        )


@dataclass
class KnowledgeEdge:
    """Arco generico del grafo."""

    source: str
    target: str
    relationship: str
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "KnowledgeEdge":
        return cls(
            source=str(payload.get("source", "")),
            target=str(payload.get("target", "")),
            relationship=str(payload.get("relationship", "")),
            properties=dict(payload.get("properties") or {}),
        )


@dataclass
class KnowledgeGraphSnapshot:
    """Snapshot serializzabile del grafo."""

    nodes: list[KnowledgeNode] = field(default_factory=list)
    edges: list[KnowledgeEdge] = field(default_factory=list)
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "KnowledgeGraphSnapshot":
        return cls(
            schema_version=int(payload.get("schema_version", 1) or 1),
            nodes=[
                KnowledgeNode.from_dict(node)
                for node in payload.get("nodes", []) or []
                if isinstance(node, dict)
            ],
            edges=[
                KnowledgeEdge.from_dict(edge)
                for edge in payload.get("edges", []) or []
                if isinstance(edge, dict)
            ],
        )
