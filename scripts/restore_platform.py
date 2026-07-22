"""Restore a SQLite platform backup with explicit confirmation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.platform.persistence import PlatformRepository


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backup", type=Path)
    parser.add_argument("--confirm", action="store_true", help="Required to overwrite the configured SQLite database")
    args = parser.parse_args()
    if not args.confirm:
        parser.error("--confirm is required")
    if not args.backup.is_file():
        parser.error("backup file does not exist")
    repository = PlatformRepository()
    if repository.backend != "sqlite":
        parser.error("PostgreSQL restores must use the documented pg_restore procedure")
    print(f"restored={repository.restore(args.backup)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
