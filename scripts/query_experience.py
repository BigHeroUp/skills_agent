"""Query deterministic analytical experience from the CLI."""

from __future__ import annotations

import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from services.experience.experience_engine import AnalyticalExperienceEngine
from services.experience.experience_query import query_experience
from services.experience.experience_store import ExperienceStore
from services.knowledge_graph.store import KnowledgeGraphStore


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print('Uso: python3 scripts/query_experience.py "cosa abbiamo imparato sui response_time?"')
        return 1

    try:
        engine = AnalyticalExperienceEngine(
            experience_path=REPOSITORY_ROOT / ExperienceStore.DEFAULT_PATH,
            kg_path=REPOSITORY_ROOT / KnowledgeGraphStore.DEFAULT_PATH,
        )
        result = query_experience(" ".join(args).strip(), engine=engine)
    except Exception as exc:
        print(f"Errore query experience: {exc}")
        return 1

    print(result["answer"])
    print(f"Confidenza: {result['confidence']:.2f}")
    print(f"Tipo esecuzione: {result['execution_type']}")

    recommendations = result.get("recommendations") or []
    if recommendations:
        print("Raccomandazioni:")
        for item in recommendations[:5]:
            print(f"- [{item['priority']}] {item['step']}")

    matches = result.get("matches") or []
    if matches and isinstance(matches[0], dict):
        print("Esperienze rilevanti:")
        for item in matches[:5]:
            print(f"- {item.get('title', item.get('id', 'experience'))}")
    return 0 if result.get("success", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
