"""Preview or apply tenant-safe analysis retention."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.platform.persistence import PlatformRepository


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, required=True, help="Retain analyses newer than this many days")
    parser.add_argument("--tenant-id", help="Optional tenant scope")
    parser.add_argument("--apply", action="store_true", help="Delete candidates; default is dry-run")
    args = parser.parse_args()
    if args.days < 1:
        parser.error("--days must be at least 1")
    cutoff = (datetime.now(timezone.utc) - timedelta(days=args.days)).isoformat()
    repository = PlatformRepository()
    candidates = repository.retention_candidates(cutoff, args.tenant_id)
    print(f"mode={'apply' if args.apply else 'dry-run'} cutoff={cutoff} candidates={len(candidates)}")
    for item in candidates[:20]:
        print(f"{item['tenant_id']} {item['id']} {item['status']} {item['created_at']}")
    if args.apply:
        print(f"deleted={repository.purge_analyses_before(cutoff, args.tenant_id)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
