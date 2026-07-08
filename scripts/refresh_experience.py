"""Refresh deterministic analytical experience from the local Knowledge Graph."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from services.experience.experience_engine import AnalyticalExperienceEngine
from services.experience.experience_store import ExperienceStore
from services.knowledge_graph.store import KnowledgeGraphStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refresh deterministic analytical experience")
    parser.add_argument("--limit", type=int, default=20, help="Maximum number of analysis runs to scan")
    args = parser.parse_args(argv)

    try:
        engine = AnalyticalExperienceEngine(
            experience_path=REPOSITORY_ROOT / ExperienceStore.DEFAULT_PATH,
            kg_path=REPOSITORY_ROOT / KnowledgeGraphStore.DEFAULT_PATH,
        )
        result = engine.refresh_experience_from_kg(limit=max(0, args.limit))
    except Exception as exc:
        print(f"Errore refresh experience: {exc}")
        return 1

    print(f"Experience refresh completato. Esperienze create: {result.get('experience_count', 0)}")
    if result.get("experience_ids"):
        print("Experience IDs:")
        for experience_id in result["experience_ids"][:10]:
            print(f"- {experience_id}")
    if result.get("message"):
        print(result["message"])
    print(f"Tipo esecuzione: {result['execution_type']}")
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
