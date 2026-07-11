"""Read-only CLI for deterministic Knowledge Graph structural validation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from services.knowledge_graph.governance import ValidationMode
from services.knowledge_graph.store import KnowledgeGraphStore
from services.knowledge_graph.validation import QualityStatus, validate_graph


EXIT_VALID = 0
EXIT_INVALID = 1
EXIT_UNREADABLE = 2
EXIT_UNSUPPORTED = 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate the local Knowledge Graph without modifying it",
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=REPOSITORY_ROOT / KnowledgeGraphStore.DEFAULT_PATH,
        help="Knowledge Graph JSON path",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--mode",
        choices=tuple(mode.value for mode in ValidationMode),
        default=ValidationMode.PERMISSIVE.value,
        help="Validation admissibility mode (default: permissive)",
    )
    return parser


def exit_code_for_status(status: QualityStatus) -> int:
    if status == QualityStatus.UNSUPPORTED:
        return EXIT_UNSUPPORTED
    if status == QualityStatus.UNREADABLE:
        return EXIT_UNREADABLE
    if status == QualityStatus.INVALID:
        return EXIT_INVALID
    return EXIT_VALID


def format_text(result) -> str:
    report = result.report
    lines = [
        "Knowledge Graph structural validation",
        f"Status: {report.status.value}",
        f"Mode: {result.mode.value}",
        f"Schema version: {report.graph_schema_version}",
        f"Can consume: {str(report.can_consume).lower()}",
        f"Can write: {str(report.can_write).lower()}",
        f"Accepted nodes: {report.accepted_node_count}",
        f"Accepted edges: {report.accepted_edge_count}",
        f"Quarantined records: {report.quarantined_record_count}",
        (
            "Issues: "
            f"errors={report.severity_counts.get('error', 0)} "
            f"warnings={report.severity_counts.get('warning', 0)} "
            f"info={report.severity_counts.get('info', 0)}"
        ),
    ]
    if report.fingerprint:
        lines.append(f"Raw fingerprint: {report.fingerprint.value}")
    if report.issues:
        lines.append("Findings:")
        for issue in report.issues:
            lines.append(
                f"- [{issue.severity.value}] {issue.code} {issue.location}: {issue.message}"
            )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = validate_graph(args.path, mode=args.mode)
    if args.format == "json":
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False))
    else:
        print(format_text(result))
    return exit_code_for_status(result.report.status)


if __name__ == "__main__":
    raise SystemExit(main())
