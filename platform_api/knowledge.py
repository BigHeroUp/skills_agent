"""Tenant-scoped read model for the Knowledge Intelligence workspace."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.experience.experience_store import ExperienceStore
from services.knowledge_graph.query_engine import KnowledgeGraphQueryEngine
from services.knowledge_graph.store import KnowledgeGraphStore
from services.knowledge_graph.validation import validate_graph


def tenant_paths(root: str | Path, tenant_id: str) -> dict[str, Path]:
    tenant_root = Path(root) / tenant_id
    return {
        "root": tenant_root,
        "graph": tenant_root / "knowledge_graph.json",
        "experience": tenant_root / "experience.json",
    }


def build_workspace_payload(
    graph_path: str | Path,
    experience_path: str | Path,
    analyses: list[dict[str, Any]],
    *,
    node_type: str = "",
    search: str = "",
    limit: int = 250,
    latest_intelligence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a bounded, deterministic projection for UI and API consumers."""
    path = Path(graph_path)
    store = KnowledgeGraphStore(path)
    snapshot = store.load()
    nodes = snapshot.nodes
    clean_type = str(node_type or "").strip()
    clean_search = str(search or "").strip().lower()
    if clean_type:
        nodes = [node for node in nodes if node.type == clean_type]
    if clean_search:
        nodes = [
            node for node in nodes
            if clean_search in node.label.lower()
            or clean_search in node.id.lower()
            or clean_search in str(node.properties).lower()
        ]
    bounded_limit = max(1, min(int(limit), 1000))
    visible_nodes = nodes[:bounded_limit]
    visible_ids = {node.id for node in visible_nodes}
    visible_edges = [
        edge for edge in snapshot.edges
        if edge.source in visible_ids and edge.target in visible_ids
    ][: bounded_limit * 4]

    validation = validate_graph(path).to_dict()
    report = validation.get("report") or {}
    experiences = ExperienceStore(experience_path).load()
    node_types = Counter(node.type for node in snapshot.nodes)
    relationships = Counter(edge.relationship for edge in snapshot.edges)
    quality = {
        "status": report.get("status", "not_available"),
        "can_consume": bool(validation.get("can_consume")),
        "can_write": bool(validation.get("can_write")),
        "issues": report.get("issues") or [],
        "dimensions": report.get("dimensions") or [],
        "quarantined_count": len(validation.get("quarantined_records") or []),
        "is_complete": bool(validation.get("is_complete")),
    }
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "exists": path.exists(),
            "updated_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
            if path.exists() else None,
            "schema_version": snapshot.schema_version,
        },
        "summary": {
            "nodes": len(snapshot.nodes),
            "edges": len(snapshot.edges),
            "node_types": len(node_types),
            "experiences": len(experiences),
            "analyses": len(analyses),
            "visible_nodes": len(visible_nodes),
        },
        "node_types": dict(sorted(node_types.items())),
        "relationships": dict(sorted(relationships.items())),
        "nodes": [node.to_dict() for node in visible_nodes],
        "edges": [edge.to_dict() for edge in visible_edges],
        "quality": quality,
        "experiences": [item.to_dict() for item in experiences[-30:]],
        "analyses": analyses[:20],
        "intelligence": latest_intelligence or {},
        "filters": {"node_type": clean_type, "search": clean_search, "limit": bounded_limit},
    }


def answer_workspace_question(graph_path: str | Path, question: str) -> dict[str, Any]:
    return KnowledgeGraphQueryEngine(path=graph_path).answer_question_deterministic(question)
