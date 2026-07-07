"""Mostra le ultime run analitiche salvate nel Knowledge Graph locale."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from services.knowledge_graph.query_engine import KnowledgeGraphQueryEngine
from services.knowledge_graph.store import KnowledgeGraphStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mostra le ultime analisi dal Knowledge Graph locale.")
    parser.add_argument("--limit", type=int, default=5, help="Numero massimo di analisi da mostrare.")
    args = parser.parse_args(argv)

    path = REPOSITORY_ROOT / KnowledgeGraphStore.DEFAULT_PATH
    engine = KnowledgeGraphQueryEngine(path=path)
    runs = engine.get_latest_analysis_runs(limit=args.limit)
    if not runs:
        print(f"Nessuna analisi trovata nel Knowledge Graph: {path}")
        print("Esegui una pipeline analitica o indicizza il grafo prima di riprovare.")
        return 0

    print(f"Ultime analisi nel Knowledge Graph ({len(runs)}):")
    for index, run in enumerate(runs, start=1):
        props = run.get("properties") or {}
        lineage = engine.get_analysis_lineage(run["id"])
        print(f"\n{index}. {run.get('label')}")
        print(f"   id: {run.get('id')}")
        print(f"   created_at: {props.get('created_at')}")
        print(f"   source_type: {props.get('source_type')}")
        print(f"   righe/colonne: {props.get('row_count')} / {props.get('column_count')}")
        print(f"   primary_metric: {props.get('primary_metric')}")
        print(f"   time_axis: {props.get('time_axis')}")
        print(f"   confidence_score: {props.get('confidence_score')}")
        print(
            "   lineage: "
            f"dataset={len(lineage['dataset'])}, "
            f"colonne={len(lineage['columns'])}, "
            f"insight={len(lineage['insights'])}, "
            f"anomalie={len(lineage['anomalies'])}, "
            f"root_cause={len(lineage['root_causes'])}, "
            f"report={len(lineage['reports'])}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
