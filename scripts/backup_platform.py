"""Create a timestamped SQLite backup; PostgreSQL deployments use pg_dump."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.platform.persistence import PlatformRepository


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="backups")
    args = parser.parse_args(argv)
    repository = PlatformRepository()
    if repository.backend == "postgresql":
        print("PostgreSQL detected: run pg_dump against DATABASE_URL from the secured host.")
        return 2
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = Path(args.output_dir) / f"platform-{timestamp}.db"
    repository.backup(destination)
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
