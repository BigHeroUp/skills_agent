#!/usr/bin/env python3
"""Scanner leggero per evitare segreti nei file versionabili."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"OPENAI_API_KEY\s*=\s*sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"(?i)(password|passwd|pwd)\s*=\s*['\"][^'\"]{8,}['\"]"),
    re.compile(r"(?i)(token|api[_-]?key|secret)\s*=\s*['\"][^'\"]{12,}['\"]"),
]


ALLOWED_PLACEHOLDERS = {
    "OPENAI_API_KEY=sk-...",
}


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [Path(line.strip()) for line in result.stdout.splitlines() if line.strip()]


def scan_file(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []

    findings: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if any(placeholder in line for placeholder in ALLOWED_PLACEHOLDERS):
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(line):
                findings.append(f"{path}:{line_number}")
                break
    return findings


def main() -> int:
    findings: list[str] = []
    for path in tracked_files():
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".db", ".pyc"}:
            continue
        findings.extend(scan_file(path))

    if findings:
        print("Possibili segreti trovati nei file versionati:")
        for finding in findings:
            print(f"- {finding}")
        return 1

    print("OK nessun segreto rilevato nei file versionati")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
