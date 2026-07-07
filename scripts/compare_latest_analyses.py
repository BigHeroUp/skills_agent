"""Confronta le ultime due analisi nel Knowledge Graph locale."""

from __future__ import annotations

import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from services.knowledge_graph.analysis_comparator import summarize_comparison
from services.knowledge_graph.query_engine import KnowledgeGraphQueryEngine
from services.knowledge_graph.store import KnowledgeGraphStore


def main() -> int:
    path = REPOSITORY_ROOT / KnowledgeGraphStore.DEFAULT_PATH
    engine = KnowledgeGraphQueryEngine(path=path)
    comparison = engine.compare_latest_analysis_runs(limit=2)
    print(summarize_comparison(comparison))
    if comparison.get("status") != "computed":
        print(f"Knowledge Graph: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
