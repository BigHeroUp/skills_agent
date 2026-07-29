"""Fail CI when a non-feedback private-beta gate regresses."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from validation_lab.beta_readiness import BetaReadinessEvaluator


def main() -> int:
    evidence = json.loads((ROOT / "validation_lab/beta_evidence.current.json").read_text(encoding="utf-8"))
    result = BetaReadinessEvaluator().evaluate(evidence)
    unexpected = [gate for gate in result["failed_gates"] if gate != "validated_accuracy"]
    print(json.dumps({"status": "passed" if not unexpected else "failed", "unexpected_failed_gates": unexpected}))
    return 0 if not unexpected else 2


if __name__ == "__main__":
    raise SystemExit(main())
