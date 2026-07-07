"""Interroga il Knowledge Graph locale con risposte deterministiche."""

from __future__ import annotations

import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from services.knowledge_graph.query_engine import KnowledgeGraphQueryEngine
from services.knowledge_graph.store import KnowledgeGraphStore


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print('Uso: python scripts/query_knowledge_graph.py "quali funzioni generano grafici?"')
        return 1

    question = " ".join(args).strip()
    path = REPOSITORY_ROOT / KnowledgeGraphStore.DEFAULT_PATH
    engine = KnowledgeGraphQueryEngine(path=path)
    result = engine.answer_question_deterministic(question)

    print(result["answer"])
    print(f"Confidenza: {result['confidence']:.2f}")
    print(f"Tipo esecuzione: {result['execution_type']}")

    matches = result.get("matches") or []
    if matches:
        print("Match:")
        for index, match in enumerate(matches[:10], start=1):
            label = match.get("label") or match.get("id")
            node_type = match.get("type", "node")
            node_id = match.get("id", "")
            print(f"{index}. [{node_type}] {label} ({node_id})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
