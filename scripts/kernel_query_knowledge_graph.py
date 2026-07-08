"""Kernel-based CLI entrypoint for deterministic Knowledge Graph queries."""

from __future__ import annotations

import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from core.kernel import create_default_kernel
from services.knowledge_graph.store import KnowledgeGraphStore


def execute_kernel_query(question: str) -> tuple[int, dict]:
    """Execute a deterministic Knowledge Graph query through the kernel."""

    kernel = create_default_kernel(path=REPOSITORY_ROOT / KnowledgeGraphStore.DEFAULT_PATH)
    response = kernel.execute_capability(
        "knowledge_graph.query",
        payload={
            "question": question,
            "mode": "deterministic",
        },
    )
    payload = response.result if response.success else {
        "question": question,
        "answer": response.errors[0] if response.errors else "Errore sconosciuto.",
        "matches": [],
        "confidence": 0.0,
        "execution_type": "deterministic_kg_query",
    }
    payload["success"] = response.success
    return (0 if response.success else 1), payload


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print(
            'Uso: python3 scripts/kernel_query_knowledge_graph.py "quali funzioni generano grafici?"'
        )
        return 1

    question = " ".join(args).strip()
    exit_code, result = execute_kernel_query(question)

    print(result["answer"])
    print(f"Confidenza: {result['confidence']:.2f}")
    print(f"Tipo esecuzione: {result['execution_type']}")

    matches = result.get("matches") or []
    if matches:
        print("Primi match:")
        for index, match in enumerate(matches[:5], start=1):
            label = match.get("label") or match.get("id") or "match"
            node_type = match.get("type", "node")
            node_id = match.get("id", "")
            print(f"{index}. [{node_type}] {label} ({node_id})")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
