"""Persistenza JSON locale per il Knowledge Graph interno."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.knowledge_graph.models import (
    KnowledgeEdge,
    KnowledgeGraphSnapshot,
    KnowledgeNode,
)


class KnowledgeGraphStore:
    """Store JSON append/update semplice, senza database esterni."""

    DEFAULT_PATH = Path("data") / "knowledge_graph" / "knowledge_graph.json"

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path is not None else self.DEFAULT_PATH
        self._nodes: dict[str, KnowledgeNode] = {}
        self._edges: dict[tuple[str, str, str], KnowledgeEdge] = {}

    def load(self) -> KnowledgeGraphSnapshot:
        """Carica lo snapshot da disco, se presente."""
        self._nodes = {}
        self._edges = {}
        if not self.path.exists():
            return self.get_snapshot()

        with self.path.open("r", encoding="utf-8") as file:
            payload = json.load(file)

        snapshot = KnowledgeGraphSnapshot.from_dict(payload if isinstance(payload, dict) else {})
        for node in snapshot.nodes:
            self.upsert_node(node)
        for edge in snapshot.edges:
            self.upsert_edge(edge)
        return self.get_snapshot()

    def save(self, snapshot: KnowledgeGraphSnapshot | None = None) -> KnowledgeGraphSnapshot:
        """Salva lo snapshot corrente o quello passato come argomento."""
        if snapshot is not None:
            self._replace(snapshot)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        current = self.get_snapshot()
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(self._json_safe(current.to_dict()), file, ensure_ascii=False, indent=2, sort_keys=True)
        return current

    def upsert_node(self, node: KnowledgeNode) -> None:
        """Inserisce o aggiorna un nodo per id."""
        if not node.id:
            return
        self._nodes[node.id] = KnowledgeNode(
            id=node.id,
            type=node.type,
            label=node.label,
            properties=self._json_safe(node.properties),
        )

    def upsert_edge(self, edge: KnowledgeEdge) -> None:
        """Inserisce o aggiorna un arco per source, target e relazione."""
        if not edge.source or not edge.target or not edge.relationship:
            return
        self._edges[(edge.source, edge.target, edge.relationship)] = KnowledgeEdge(
            source=edge.source,
            target=edge.target,
            relationship=edge.relationship,
            properties=self._json_safe(edge.properties),
        )

    def get_snapshot(self) -> KnowledgeGraphSnapshot:
        """Restituisce una copia ordinata e serializzabile dello stato corrente."""
        nodes = [self._nodes[key] for key in sorted(self._nodes)]
        edges = [
            self._edges[key]
            for key in sorted(self._edges, key=lambda item: (item[0], item[1], item[2]))
        ]
        return KnowledgeGraphSnapshot(nodes=nodes, edges=edges)

    def clear(self) -> None:
        """Svuota lo store in memoria e rimuove il file JSON locale."""
        self._nodes = {}
        self._edges = {}
        if self.path.exists():
            self.path.unlink()

    def _replace(self, snapshot: KnowledgeGraphSnapshot) -> None:
        self._nodes = {}
        self._edges = {}
        for node in snapshot.nodes:
            self.upsert_node(node)
        for edge in snapshot.edges:
            self.upsert_edge(edge)

    def _json_safe(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): self._json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._json_safe(item) for item in value]
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return str(value)
