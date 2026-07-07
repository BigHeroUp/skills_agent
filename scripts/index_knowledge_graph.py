"""Indicizza il codice Python nel Knowledge Graph locale."""

from __future__ import annotations

import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from services.knowledge_graph.code_indexer import PythonCodeIndexer
from services.knowledge_graph.store import KnowledgeGraphStore


def main() -> int:
    store = KnowledgeGraphStore(REPOSITORY_ROOT / KnowledgeGraphStore.DEFAULT_PATH)
    store.load()
    snapshot = PythonCodeIndexer(REPOSITORY_ROOT).index_repository(store)
    saved = store.save(snapshot)
    print(f"Knowledge graph salvato in: {store.path}")
    print(f"Nodi: {len(saved.nodes)}")
    print(f"Archi: {len(saved.edges)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
