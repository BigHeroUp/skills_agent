"""Caricamento locale dei domain intelligence pack."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


class DomainPackLoader:
    """Scopre, valida e carica domain pack senza chiamate OpenAI."""

    REQUIRED_FILES = (
        "domain_pack.yaml",
        "patterns.json",
        "kpi_definitions.json",
        "strategy_rules.json",
        "questions.json",
        "terminology.json",
        "report_template.md",
    )

    SCHEMA_VERSION = 1

    def __init__(self, base_path: str | Path | None = None):
        self.base_path = Path(base_path) if base_path is not None else (
            Path(__file__).resolve().parents[1] / "domain_packs"
        )

    def list_available_packs(self) -> list[dict]:
        """Restituisce i pack disponibili senza fallire su directory invalide."""
        if not self.base_path.exists() or not self.base_path.is_dir():
            return []

        packs = []
        for directory in sorted(self.base_path.iterdir()):
            if not directory.is_dir():
                continue
            manifest_path = directory / "domain_pack.yaml"
            manifest = {}
            if manifest_path.exists():
                try:
                    manifest = self._read_manifest(manifest_path)
                except ValueError:
                    manifest = {}
            validation = self.validate_pack(directory.name)
            pack_id = str(manifest.get("pack_id") or directory.name)
            packs.append(self._json_safe({
                "pack_id": pack_id,
                "directory": directory.name,
                "name": manifest.get("name", pack_id),
                "description": manifest.get("description", ""),
                "version": manifest.get("version"),
                "valid": validation["valid"],
                "missing_files": validation["missing_files"],
            }))
        return packs

    def load_pack(self, pack_id: str) -> dict:
        """Carica un pack valido in formato JSON-safe."""
        validation = self.validate_pack(pack_id)
        if not validation["valid"]:
            raise ValueError(
                f"Domain pack '{pack_id}' non valido: "
                + "; ".join(validation["errors"])
            )

        pack_dir = self._pack_dir(pack_id)
        manifest = self._read_manifest(pack_dir / "domain_pack.yaml")
        data = {
            "schema_version": self.SCHEMA_VERSION,
            "pack_id": str(manifest.get("pack_id") or pack_id),
            "directory": pack_id,
            "manifest": manifest,
            "patterns": self._read_json(pack_dir / "patterns.json"),
            "kpi_definitions": self._read_json(pack_dir / "kpi_definitions.json"),
            "strategy_rules": self._read_json(pack_dir / "strategy_rules.json"),
            "questions": self._read_json(pack_dir / "questions.json"),
            "terminology": self._read_json(pack_dir / "terminology.json"),
            "report_template": (pack_dir / "report_template.md").read_text(encoding="utf-8"),
        }
        return self._json_safe(data)

    def validate_pack(self, pack_id: str) -> dict:
        """Verifica presenza e leggibilita dei file obbligatori."""
        pack_dir = self._pack_dir(pack_id)
        errors: list[str] = []
        missing_files: list[str] = []

        if not pack_dir.exists() or not pack_dir.is_dir():
            return {
                "pack_id": pack_id,
                "valid": False,
                "missing_files": list(self.REQUIRED_FILES),
                "errors": [f"Directory domain pack non trovata: {pack_id}"],
            }

        for file_name in self.REQUIRED_FILES:
            if not (pack_dir / file_name).exists():
                missing_files.append(file_name)
        if missing_files:
            errors.append("File obbligatori mancanti: " + ", ".join(missing_files))

        if not missing_files:
            try:
                manifest = self._read_manifest(pack_dir / "domain_pack.yaml")
                if not manifest.get("pack_id"):
                    errors.append("domain_pack.yaml non contiene pack_id.")
            except ValueError as exc:
                errors.append(str(exc))

            for file_name in (
                "patterns.json",
                "kpi_definitions.json",
                "strategy_rules.json",
                "questions.json",
                "terminology.json",
            ):
                try:
                    self._read_json(pack_dir / file_name)
                except ValueError as exc:
                    errors.append(str(exc))

        return self._json_safe({
            "pack_id": pack_id,
            "valid": not errors,
            "missing_files": missing_files,
            "errors": errors,
        })

    def suggest_pack(
        self,
        user_request: str,
        dataframe_metadata: dict | None = None,
    ) -> dict | None:
        """Suggerisce il pack piu coerente usando solo segnali locali."""
        request = self._normalize(user_request)
        metadata = dataframe_metadata if isinstance(dataframe_metadata, dict) else {}
        columns = [self._normalize(column) for column in metadata.get("columns", [])]
        best: dict[str, Any] | None = None

        for available in self.list_available_packs():
            if not available.get("valid"):
                continue
            pack = self.load_pack(str(available["directory"]))
            score, matched_terms, metadata_signals = self._score_pack(
                pack,
                request,
                columns,
            )
            if score <= 0:
                continue
            candidate = {
                "pack_id": pack["pack_id"],
                "name": pack["manifest"].get("name", pack["pack_id"]),
                "description": pack["manifest"].get("description", ""),
                "confidence_score": round(min(score, 0.99), 4),
                "matched_terms": matched_terms,
                "metadata_signals": metadata_signals,
                "reason": self._suggestion_reason(matched_terms, metadata_signals),
            }
            if best is None or candidate["confidence_score"] > best["confidence_score"]:
                best = candidate

        if best is None or best["confidence_score"] < 0.18:
            return None
        return self._json_safe(best)

    def export_pack_knowledge(self, pack_id: str) -> dict:
        """Esporta la conoscenza del pack in forma serializzabile."""
        return self.load_pack(pack_id)

    def _score_pack(
        self,
        pack: dict,
        request: str,
        columns: list[str],
    ) -> tuple[float, list[str], list[str]]:
        terms = self._pack_terms(pack)
        matched_terms = [
            term for term in terms
            if term and self._term_matches(request, term)
        ]
        metadata_signals = [
            term for term in terms
            if term and any(self._term_matches(column, term) for column in columns)
        ]
        score = min(0.7, len(matched_terms) * 0.08)
        score += min(0.35, len(metadata_signals) * 0.06)
        if request and pack.get("pack_id") and self._term_matches(request, pack["pack_id"]):
            score += 0.2
        return score, self._unique(matched_terms)[:20], self._unique(metadata_signals)[:20]

    def _pack_terms(self, pack: dict) -> list[str]:
        manifest = pack.get("manifest") or {}
        terminology = pack.get("terminology") or {}
        terms: list[str] = []
        terms.extend(manifest.get("keywords") or [])
        terms.extend(terminology.get("concepts") or [])
        for values in (terminology.get("synonyms") or {}).values():
            terms.extend(values if isinstance(values, list) else [values])
        for values in (terminology.get("column_hints") or {}).values():
            terms.extend(values if isinstance(values, list) else [values])
        for pattern in pack.get("patterns") or []:
            if isinstance(pattern, dict):
                terms.append(pattern.get("pattern_id", ""))
                terms.extend(pattern.get("trigger_keywords") or [])
        return self._unique([self._normalize(term) for term in terms if term])

    def _suggestion_reason(self, matched_terms: list[str], metadata_signals: list[str]) -> str:
        parts = []
        if matched_terms:
            parts.append("richiesta coerente con: " + ", ".join(matched_terms[:5]))
        if metadata_signals:
            parts.append("metadata coerenti con: " + ", ".join(metadata_signals[:5]))
        return "; ".join(parts) if parts else "segnali deboli ma compatibili"

    def _pack_dir(self, pack_id: str) -> Path:
        clean_id = str(pack_id or "").strip()
        if not clean_id or clean_id in {".", ".."} or "/" in clean_id or "\\" in clean_id:
            return self.base_path / "__invalid__"
        return self.base_path / clean_id

    def _read_manifest(self, path: Path) -> dict:
        text = path.read_text(encoding="utf-8")
        try:
            import yaml  # type: ignore
        except ImportError:
            return self._parse_minimal_yaml(text, path)
        try:
            data = yaml.safe_load(text) or {}
        except Exception as exc:
            raise ValueError(f"Manifest YAML non valido {path.name}: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError(f"Manifest YAML non valido {path.name}: atteso oggetto.")
        return self._json_safe(data)

    def _parse_minimal_yaml(self, text: str, path: Path) -> dict:
        data: dict[str, Any] = {}
        current_key: str | None = None
        for raw_line in text.splitlines():
            line = raw_line.rstrip()
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("- "):
                if current_key is None:
                    raise ValueError(f"YAML minimale non valido {path.name}: lista senza chiave.")
                data.setdefault(current_key, []).append(self._coerce_scalar(stripped[2:].strip()))
                continue
            if ":" not in stripped:
                raise ValueError(f"YAML minimale non valido {path.name}: riga '{stripped}'.")
            key, value = stripped.split(":", 1)
            current_key = key.strip()
            value = value.strip()
            data[current_key] = [] if value == "" else self._coerce_scalar(value)
        return data

    def _read_json(self, path: Path) -> Any:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSON non valido {path.name}: {exc}") from exc

    def _coerce_scalar(self, value: str) -> Any:
        if value.lower() in {"true", "false"}:
            return value.lower() == "true"
        try:
            return int(value)
        except ValueError:
            return value.strip("\"'")

    def _term_matches(self, value: str, term: str) -> bool:
        normalized_term = self._normalize(term)
        if not value or not normalized_term:
            return False
        if " " in normalized_term:
            return normalized_term in value
        return bool(re.search(rf"\b{re.escape(normalized_term)}\w*\b", value))

    def _normalize(self, value: Any) -> str:
        normalized = re.sub(r"[_\-/]+", " ", str(value or "").lower())
        return re.sub(r"\s+", " ", normalized).strip()

    def _unique(self, values: list[Any]) -> list[Any]:
        output = []
        for value in values:
            if value not in output:
                output.append(value)
        return output

    def _json_safe(self, value: Any) -> Any:
        return json.loads(json.dumps(value, ensure_ascii=False, default=str))
