"""
Validazione deterministica per query Oracle read-only.

Il connettore Oracle deve accettare solo query di lettura. Questa utility
centralizza le regole per evitare controlli ad hoc sparsi nel codice.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


FORBIDDEN_KEYWORDS = {
    "ALTER",
    "CREATE",
    "DELETE",
    "DROP",
    "EXEC",
    "EXECUTE",
    "GRANT",
    "INSERT",
    "MERGE",
    "REVOKE",
    "TRUNCATE",
    "UPDATE",
}


@dataclass(frozen=True)
class QueryValidationResult:
    """Risultato della validazione Oracle."""

    is_valid: bool
    reason: str = ""
    normalized_sql: str = ""


class QuerySafetyValidator:
    """Valida query Oracle secondo il vincolo applicativo read-only."""

    @staticmethod
    def validate_read_only(sql: str) -> QueryValidationResult:
        if not sql or not sql.strip():
            return QueryValidationResult(False, "La query Oracle e vuota.")

        without_comments = QuerySafetyValidator._strip_comments(sql)
        normalized = QuerySafetyValidator._normalize(without_comments)

        if not normalized:
            return QueryValidationResult(False, "La query Oracle contiene solo commenti o spazi.")

        statements = [part.strip() for part in normalized.split(";") if part.strip()]
        if len(statements) != 1:
            return QueryValidationResult(False, "E consentita una sola query per esecuzione.")

        statement = statements[0].lstrip("(").strip()
        upper_statement = statement.upper()
        if not upper_statement.startswith(("SELECT ", "SELECT\n", "WITH ", "WITH\n")) and upper_statement not in {"SELECT", "WITH"}:
            return QueryValidationResult(False, "Sono consentite solo query Oracle SELECT o WITH.", normalized)

        tokens = set(re.findall(r"\b[A-Z_]+\b", upper_statement))
        forbidden = sorted(tokens.intersection(FORBIDDEN_KEYWORDS))
        if forbidden:
            return QueryValidationResult(
                False,
                f"Query Oracle bloccata: keyword non consentite: {', '.join(forbidden)}.",
                normalized,
            )

        return QueryValidationResult(True, "", normalized)

    @staticmethod
    def assert_read_only(sql: str) -> None:
        result = QuerySafetyValidator.validate_read_only(sql)
        if not result.is_valid:
            raise ValueError(result.reason)

    @staticmethod
    def _strip_comments(sql: str) -> str:
        no_block_comments = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
        return re.sub(r"--.*?$", " ", no_block_comments, flags=re.MULTILINE)

    @staticmethod
    def _normalize(sql: str) -> str:
        return re.sub(r"\s+", " ", sql).strip()
