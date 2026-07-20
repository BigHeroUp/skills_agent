"""Read-only production readiness report for local runtime resources."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from config import get_experience_store_max_bytes, get_knowledge_graph_max_bytes
from services.experience.experience_store import ExperienceStore
from services.knowledge_graph.store import KnowledgeGraphStore


def build_runtime_health(
    *,
    kg_path: str | Path = KnowledgeGraphStore.DEFAULT_PATH,
    experience_path: str | Path = ExperienceStore.DEFAULT_PATH,
) -> dict[str, Any]:
    resources = {
        "knowledge_graph": _resource(kg_path, get_knowledge_graph_max_bytes(), required=True),
        "experience_store": _resource(
            experience_path, get_experience_store_max_bytes(), required=False
        ),
    }
    healthy = all(item["status"] in {"ok", "not_initialized"} for item in resources.values())
    return {
        "status": "healthy" if healthy else "unhealthy",
        "resources": resources,
        "execution_type": "production_health_check",
    }


def _resource(path: str | Path, limit: int, *, required: bool) -> dict[str, Any]:
    target = Path(path)
    if not target.exists():
        return {
            "status": "missing" if required else "not_initialized",
            "path": str(target),
            "size_bytes": 0,
            "limit_bytes": limit,
        }
    size = target.stat().st_size
    return {
        "status": "ok" if size <= limit else "limit_exceeded",
        "path": str(target),
        "size_bytes": size,
        "limit_bytes": limit,
    }
