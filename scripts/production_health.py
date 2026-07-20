"""CLI health check for production runtime resources."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from services.production.health import build_runtime_health


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--knowledge-graph", default=None)
    parser.add_argument("--experience-store", default=None)
    args = parser.parse_args(argv)
    kwargs = {}
    if args.knowledge_graph:
        kwargs["kg_path"] = args.knowledge_graph
    if args.experience_store:
        kwargs["experience_path"] = args.experience_store
    report = build_runtime_health(**kwargs)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["status"] == "healthy" else 1


if __name__ == "__main__":
    raise SystemExit(main())
