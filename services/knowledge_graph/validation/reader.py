"""Lossless reader for Knowledge Graph JSON documents."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from services.knowledge_graph.domain import (
    DuplicateJsonKey,
    GraphFingerprint,
    GraphIssue,
    IssueSeverity,
    NonFiniteJsonNumber,
    RawGraphDocument,
    RawReadStatus,
)


class _PairObject(list):
    """Marker that distinguishes JSON objects from JSON arrays."""


@dataclass(frozen=True)
class _NonFiniteConstant:
    value: str


def _escape_pointer(value: str) -> str:
    return str(value).replace("~", "~0").replace("/", "~1")


class RawGraphDocumentReader:
    """Read a JSON file without normalizing graph records."""

    RULE_ID = "core.raw_document.read"
    RULE_VERSION = "1.0.0"

    def read(self, path: str | Path) -> RawGraphDocument:
        source_path = Path(path)
        source_name = source_path.name or "knowledge_graph.json"

        try:
            raw_bytes = source_path.read_bytes()
        except FileNotFoundError:
            return self._failure_document(
                source_name,
                RawReadStatus.MISSING,
                "raw.file_missing",
                "Il file Knowledge Graph non esiste.",
                "Generare o indicizzare il Knowledge Graph prima della validazione.",
            )
        except OSError as exc:
            return self._failure_document(
                source_name,
                RawReadStatus.UNREADABLE,
                "raw.file_unreadable",
                "Il file Knowledge Graph non è leggibile.",
                "Verificare permessi e disponibilità del file.",
                evidence={"error_type": exc.__class__.__name__},
            )

        fingerprint = GraphFingerprint.from_bytes(raw_bytes)
        try:
            original_text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            return RawGraphDocument(
                source_name=source_name,
                status=RawReadStatus.CORRUPT,
                original_bytes=raw_bytes,
                original_text=raw_bytes.decode("utf-8", errors="replace"),
                fingerprint=fingerprint,
                parse_issues=(self._issue(
                    "raw.invalid_utf8",
                    "Il documento non è codificato in UTF-8 valido.",
                    suggestion="Salvare il file come UTF-8 senza perdita di dati.",
                    evidence={"start": exc.start},
                ),),
            )

        if not original_text.strip():
            return RawGraphDocument(
                source_name=source_name,
                status=RawReadStatus.EMPTY,
                original_bytes=raw_bytes,
                original_text=original_text,
                fingerprint=fingerprint,
                parse_issues=(self._issue(
                    "raw.file_empty",
                    "Il file Knowledge Graph è vuoto.",
                    suggestion="Fornire un documento JSON con schema_version, nodes ed edges.",
                ),),
            )

        try:
            parsed = json.loads(
                original_text,
                object_pairs_hook=_PairObject,
                parse_constant=lambda value: _NonFiniteConstant(value),
            )
        except json.JSONDecodeError as exc:
            return RawGraphDocument(
                source_name=source_name,
                status=RawReadStatus.CORRUPT,
                original_bytes=raw_bytes,
                original_text=original_text,
                fingerprint=fingerprint,
                parse_issues=(self._issue(
                    "raw.json_syntax_error",
                    "Il documento non contiene JSON sintatticamente valido.",
                    suggestion="Correggere la sintassi JSON prima di ripetere la validazione.",
                    evidence={"column": exc.colno, "line": exc.lineno, "position": exc.pos},
                ),),
            )

        duplicate_keys: list[DuplicateJsonKey] = []
        non_finite_numbers: list[NonFiniteJsonNumber] = []
        root = self._materialize(
            parsed,
            location="",
            duplicate_keys=duplicate_keys,
            non_finite_numbers=non_finite_numbers,
        )
        status = RawReadStatus.VALID if isinstance(root, dict) else RawReadStatus.NON_OBJECT
        return RawGraphDocument(
            source_name=source_name,
            status=status,
            original_bytes=raw_bytes,
            original_text=original_text,
            fingerprint=fingerprint,
            root=root,
            duplicate_keys=tuple(duplicate_keys),
            non_finite_numbers=tuple(non_finite_numbers),
        )

    def _materialize(
        self,
        value: Any,
        *,
        location: str,
        duplicate_keys: list[DuplicateJsonKey],
        non_finite_numbers: list[NonFiniteJsonNumber],
    ) -> Any:
        if isinstance(value, _PairObject):
            output: dict[str, Any] = {}
            seen: set[str] = set()
            for key, item in value:
                clean_key = str(key)
                child_location = f"{location}/{_escape_pointer(clean_key)}"
                if clean_key in seen:
                    duplicate_keys.append(DuplicateJsonKey(clean_key, child_location or "/"))
                seen.add(clean_key)
                output[clean_key] = self._materialize(
                    item,
                    location=child_location,
                    duplicate_keys=duplicate_keys,
                    non_finite_numbers=non_finite_numbers,
                )
            return output
        if isinstance(value, list):
            return [
                self._materialize(
                    item,
                    location=f"{location}/{index}",
                    duplicate_keys=duplicate_keys,
                    non_finite_numbers=non_finite_numbers,
                )
                for index, item in enumerate(value)
            ]
        if isinstance(value, _NonFiniteConstant):
            non_finite_numbers.append(
                NonFiniteJsonNumber(value=value.value, location=location or "/")
            )
            return value.value
        return value

    def _failure_document(
        self,
        source_name: str,
        status: RawReadStatus,
        code: str,
        message: str,
        suggestion: str,
        evidence: dict[str, Any] | None = None,
    ) -> RawGraphDocument:
        return RawGraphDocument(
            source_name=source_name,
            status=status,
            parse_issues=(self._issue(
                code,
                message,
                suggestion=suggestion,
                evidence=evidence,
            ),),
        )

    def _issue(
        self,
        code: str,
        message: str,
        *,
        suggestion: str,
        evidence: dict[str, Any] | None = None,
    ) -> GraphIssue:
        return GraphIssue(
            code=code,
            severity=IssueSeverity.ERROR,
            category="document_structure",
            location="/",
            message=message,
            evidence=evidence or {},
            suggestion=suggestion,
            rule_id=self.RULE_ID,
            rule_version=self.RULE_VERSION,
        )
