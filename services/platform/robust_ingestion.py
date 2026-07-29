"""Bounded, defensive CSV/Excel ingestion for the authenticated portal."""

from __future__ import annotations

import csv
import io
import zipfile
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class IngestionResult:
    dataframe: pd.DataFrame
    source_type: str
    warnings: list[str]


def load_tabular_upload(data: bytes, filename: str, *, max_rows: int, max_columns: int = 500) -> IngestionResult:
    if not data:
        raise ValueError("Il file caricato è vuoto")
    lower = filename.lower()
    warnings: list[str] = []
    if lower.endswith(".csv"):
        frame, warnings = _read_csv(data, max_rows)
        source_type = "csv"
    elif lower.endswith((".xlsx", ".xls")):
        if lower.endswith(".xlsx"):
            _validate_xlsx_archive(data)
        frame = pd.read_excel(io.BytesIO(data), nrows=max_rows + 1)
        source_type = "excel"
    else:
        raise ValueError("Sono supportati soltanto file CSV ed Excel")
    if len(frame) > max_rows:
        raise ValueError(f"Il dataset supera il limite configurato di {max_rows} record")
    if len(frame.columns) > max_columns:
        raise ValueError(f"Il dataset supera il limite configurato di {max_columns} colonne")
    duplicates = frame.columns[frame.columns.duplicated()].astype(str).tolist()
    if duplicates:
        raise ValueError(f"Nomi colonna duplicati non ammessi: {', '.join(duplicates[:5])}")
    if frame.empty or not len(frame.columns):
        raise ValueError("Il file non contiene una tabella utilizzabile")
    return IngestionResult(frame, source_type, warnings)


def _read_csv(data: bytes, max_rows: int) -> tuple[pd.DataFrame, list[str]]:
    encoding = next((enc for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1") if _decodes(data, enc)), None)
    if encoding is None:
        raise ValueError("Codifica CSV non riconosciuta")
    text = data.decode(encoding)
    try:
        dialect = csv.Sniffer().sniff(text[:8192], delimiters=",;\t|")
        separator = dialect.delimiter
    except csv.Error:
        separator = ","
    frame = pd.read_csv(io.StringIO(text), sep=separator, nrows=max_rows + 1)
    warnings = []
    if encoding not in {"utf-8", "utf-8-sig"}:
        warnings.append(f"CSV convertito dalla codifica {encoding}.")
    if separator != ",":
        warnings.append(f"Separatore CSV rilevato automaticamente: {separator!r}.")
    return frame, warnings


def _decodes(data: bytes, encoding: str) -> bool:
    try:
        data.decode(encoding)
        return True
    except UnicodeDecodeError:
        return False


def _validate_xlsx_archive(data: bytes) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            compressed = sum(item.compress_size for item in archive.infolist()) or 1
            expanded = sum(item.file_size for item in archive.infolist())
            if len(archive.infolist()) > 5000 or expanded > 100 * 1024 * 1024 or expanded / compressed > 100:
                raise ValueError("Archivio Excel rifiutato: espansione non sicura")
    except zipfile.BadZipFile as exc:
        raise ValueError("File Excel non valido") from exc
