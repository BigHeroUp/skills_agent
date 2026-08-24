"""Versioned multi-tenant persistence with SQLite and PostgreSQL support."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4


SCHEMA_VERSION = 5

FEEDBACK_OUTCOMES = {"correct", "partial", "incorrect"}
FEEDBACK_SOURCES = {"external", "internal"}
FEEDBACK_VERIFICATION_STATUSES = {"pending", "verified", "rejected"}
FEEDBACK_REASON_CODES = {
    "no_issue",
    "calculation_error",
    "intent_mismatch",
    "missing_evidence",
    "unclear_output",
    "performance",
    "unsupported_request",
    "other",
}
BETA_FUNNEL_ORDER = (
    "portal_accessed",
    "plan_previewed",
    "analysis_started",
    "analysis_completed",
    "result_viewed",
    "feedback_submitted",
)
BETA_FUNNEL_EVENTS = set(BETA_FUNNEL_ORDER)


class PlatformRepository:
    def __init__(self, database_url: str | None = None):
        url_file = os.getenv("DATABASE_URL_FILE", "").strip()
        file_value = Path(url_file).read_text(encoding="utf-8").strip() if url_file else ""
        self.database_url = database_url or file_value or os.getenv(
            "DATABASE_URL", "sqlite:///data/platform/platform.db"
        )
        self.backend = "postgresql" if self.database_url.startswith(("postgres://", "postgresql://")) else "sqlite"
        self.sqlite_path = self._sqlite_path() if self.backend == "sqlite" else None
        self.migrate()

    def _sqlite_path(self) -> Path:
        raw = self.database_url.removeprefix("sqlite:///")
        path = Path(raw)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    @contextmanager
    def connect(self) -> Iterator[Any]:
        if self.backend == "postgresql":
            try:
                import psycopg
            except ImportError as exc:
                raise RuntimeError("Install psycopg[binary] for PostgreSQL support") from exc
            from psycopg.rows import dict_row
            connection = psycopg.connect(self.database_url, row_factory=dict_row)
        else:
            connection = sqlite3.connect(self.sqlite_path)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @property
    def placeholder(self) -> str:
        return "%s" if self.backend == "postgresql" else "?"

    def migrate(self) -> None:
        identity = "BIGSERIAL" if self.backend == "postgresql" else "INTEGER"
        with self.connect() as connection:
            cursor = connection.cursor()
            if self.backend == "postgresql":
                # Gunicorn may boot multiple workers simultaneously. Serialize DDL
                # so PostgreSQL does not race while creating the same relation type.
                cursor.execute("SELECT pg_advisory_xact_lock(734519002)")
            cursor.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
            cursor.execute("CREATE TABLE IF NOT EXISTS tenants (id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL)")
            cursor.execute("""CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, email TEXT NOT NULL,
                password_hash TEXT NOT NULL, role TEXT NOT NULL, created_at TEXT NOT NULL,
                UNIQUE(tenant_id, email), FOREIGN KEY(tenant_id) REFERENCES tenants(id)
            )""")
            cursor.execute(f"""CREATE TABLE IF NOT EXISTS analyses (
                sequence {identity} PRIMARY KEY{'' if self.backend == 'postgresql' else ' AUTOINCREMENT'},
                id TEXT UNIQUE NOT NULL, tenant_id TEXT NOT NULL, created_by TEXT NOT NULL,
                description TEXT NOT NULL, source_type TEXT NOT NULL, status TEXT NOT NULL,
                request_json TEXT NOT NULL, result_json TEXT, error TEXT,
                progress INTEGER NOT NULL DEFAULT 0, cancel_requested INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                FOREIGN KEY(tenant_id) REFERENCES tenants(id), FOREIGN KEY(created_by) REFERENCES users(id)
            )""")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_analyses_tenant_created ON analyses(tenant_id, created_at)")
            cursor.execute(f"""CREATE TABLE IF NOT EXISTS analysis_feedback (
                sequence {identity} PRIMARY KEY{'' if self.backend == 'postgresql' else ' AUTOINCREMENT'},
                id TEXT UNIQUE NOT NULL, tenant_id TEXT NOT NULL, analysis_id TEXT NOT NULL,
                user_id TEXT NOT NULL, rating INTEGER NOT NULL, outcome TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '', feedback_source TEXT NOT NULL DEFAULT 'unclassified',
                verification_status TEXT NOT NULL DEFAULT 'pending', verified_by TEXT,
                verified_at TEXT, reviewer_notes TEXT NOT NULL DEFAULT '',
                reason_code TEXT NOT NULL DEFAULT 'other', expected_result TEXT NOT NULL DEFAULT '',
                analysis_version TEXT NOT NULL DEFAULT 'unknown', issue_reference TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                UNIQUE(tenant_id, analysis_id, user_id),
                FOREIGN KEY(tenant_id) REFERENCES tenants(id),
                FOREIGN KEY(analysis_id) REFERENCES analyses(id),
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(verified_by) REFERENCES users(id)
            )""")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_tenant_created ON analysis_feedback(tenant_id, created_at)")
            cursor.execute(f"""CREATE TABLE IF NOT EXISTS quality_snapshots (
                sequence {identity} PRIMARY KEY{'' if self.backend == 'postgresql' else ' AUTOINCREMENT'},
                id TEXT UNIQUE NOT NULL, tenant_id TEXT NOT NULL, payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL, FOREIGN KEY(tenant_id) REFERENCES tenants(id)
            )""")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_quality_tenant_created ON quality_snapshots(tenant_id, created_at)")
            cursor.execute(f"""CREATE TABLE IF NOT EXISTS beta_funnel_events (
                sequence {identity} PRIMARY KEY{'' if self.backend == 'postgresql' else ' AUTOINCREMENT'},
                id TEXT UNIQUE NOT NULL, tenant_id TEXT NOT NULL, user_id TEXT NOT NULL,
                session_id TEXT NOT NULL, event_type TEXT NOT NULL,
                analysis_id TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
                UNIQUE(tenant_id, session_id, event_type, analysis_id),
                FOREIGN KEY(tenant_id) REFERENCES tenants(id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )""")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_beta_funnel_tenant_event ON beta_funnel_events(tenant_id, event_type, created_at)")
            self._ensure_column(cursor, "analyses", "progress", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(cursor, "analyses", "cancel_requested", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(cursor, "analysis_feedback", "feedback_source", "TEXT NOT NULL DEFAULT 'unclassified'")
            self._ensure_column(cursor, "analysis_feedback", "verification_status", "TEXT NOT NULL DEFAULT 'pending'")
            self._ensure_column(cursor, "analysis_feedback", "verified_by", "TEXT")
            self._ensure_column(cursor, "analysis_feedback", "verified_at", "TEXT")
            self._ensure_column(cursor, "analysis_feedback", "reviewer_notes", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(cursor, "analysis_feedback", "reason_code", "TEXT NOT NULL DEFAULT 'other'")
            self._ensure_column(cursor, "analysis_feedback", "expected_result", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(cursor, "analysis_feedback", "analysis_version", "TEXT NOT NULL DEFAULT 'unknown'")
            self._ensure_column(cursor, "analysis_feedback", "issue_reference", "TEXT NOT NULL DEFAULT ''")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_tenant_verification ON analysis_feedback(tenant_id, verification_status, feedback_source)")
            cursor.execute(
                f"INSERT INTO schema_migrations(version, applied_at) VALUES ({self.placeholder}, {self.placeholder}) ON CONFLICT(version) DO NOTHING",
                (SCHEMA_VERSION, self._now()),
            )

    def create_tenant_with_admin(self, name: str, email: str, password_hash: str) -> dict[str, str]:
        tenant_id, user_id, now = uuid4().hex, uuid4().hex, self._now()
        with self.connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                f"INSERT INTO tenants(id, name, created_at) VALUES ({self.placeholder},{self.placeholder},{self.placeholder})",
                (tenant_id, name.strip(), now),
            )
            cursor.execute(
                f"INSERT INTO users(id, tenant_id, email, password_hash, role, created_at) VALUES ({','.join([self.placeholder] * 6)})",
                (user_id, tenant_id, email.strip().lower(), password_hash, "admin", now),
            )
        return {"tenant_id": tenant_id, "user_id": user_id, "role": "admin"}

    def get_user_by_email(self, tenant_id: str, email: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.cursor().execute(
                f"SELECT * FROM users WHERE tenant_id={self.placeholder} AND email={self.placeholder}",
                (tenant_id, email.strip().lower()),
            ).fetchone()
        return self._row(row)

    def create_user(self, tenant_id: str, email: str, password_hash: str, role: str) -> str:
        if role not in {"admin", "analyst", "viewer"}:
            raise ValueError("Unsupported role")
        user_id = uuid4().hex
        with self.connect() as connection:
            connection.cursor().execute(
                f"INSERT INTO users(id, tenant_id, email, password_hash, role, created_at) VALUES ({','.join([self.placeholder] * 6)})",
                (user_id, tenant_id, email.strip().lower(), password_hash, role, self._now()),
            )
        return user_id

    def create_analysis(self, tenant_id: str, user_id: str, request: dict[str, Any]) -> str:
        analysis_id, now = uuid4().hex, self._now()
        records = request.get("records") if isinstance(request.get("records"), list) else []
        persisted_request = {
            key: value
            for key, value in request.items()
            if key != "records" and not str(key).startswith("_")
        }
        persisted_request["record_count"] = len(records)
        persisted_request["columns"] = sorted({str(key) for row in records if isinstance(row, dict) for key in row})
        values = (
            analysis_id, tenant_id, user_id, str(request["description"]),
            str(request.get("source_type") or "records"), "queued",
            json.dumps(persisted_request, ensure_ascii=False, default=str), None, None, now, now,
        )
        with self.connect() as connection:
            connection.cursor().execute(
                f"""INSERT INTO analyses(
                    id,tenant_id,created_by,description,source_type,status,request_json,
                    result_json,error,created_at,updated_at
                ) VALUES ({','.join([self.placeholder] * 11)})""",
                values,
            )
        return analysis_id

    def update_analysis(self, tenant_id: str, analysis_id: str, *, status: str, result=None, error=None) -> bool:
        with self.connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                f"""UPDATE analyses SET status={self.placeholder}, result_json={self.placeholder},
                    error={self.placeholder}, updated_at={self.placeholder}
                    WHERE tenant_id={self.placeholder} AND id={self.placeholder}""",
                (status, json.dumps(result, ensure_ascii=False, default=str) if result is not None else None,
                 error, self._now(), tenant_id, analysis_id),
            )
            return cursor.rowcount == 1

    def update_progress(self, tenant_id: str, analysis_id: str, progress: int, status: str = "processing") -> bool:
        with self.connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                f"UPDATE analyses SET progress={self.placeholder}, status={self.placeholder}, updated_at={self.placeholder} WHERE tenant_id={self.placeholder} AND id={self.placeholder}",
                (max(0, min(int(progress), 100)), status, self._now(), tenant_id, analysis_id),
            )
            return cursor.rowcount == 1

    def request_cancel(self, tenant_id: str, analysis_id: str) -> bool:
        with self.connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                f"UPDATE analyses SET cancel_requested=1, status={self.placeholder}, updated_at={self.placeholder} WHERE tenant_id={self.placeholder} AND id={self.placeholder} AND status IN ('queued','processing')",
                ("cancelling", self._now(), tenant_id, analysis_id),
            )
            return cursor.rowcount == 1

    def is_cancel_requested(self, tenant_id: str, analysis_id: str) -> bool:
        with self.connect() as connection:
            row = connection.cursor().execute(
                f"SELECT cancel_requested FROM analyses WHERE tenant_id={self.placeholder} AND id={self.placeholder}",
                (tenant_id, analysis_id),
            ).fetchone()
        value = row.get("cancel_requested") if isinstance(row, dict) else row[0] if row else 0
        return bool(value)

    def get_analysis(self, tenant_id: str, analysis_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.cursor().execute(
                f"SELECT * FROM analyses WHERE tenant_id={self.placeholder} AND id={self.placeholder}",
                (tenant_id, analysis_id),
            ).fetchone()
        item = self._row(row)
        if item:
            item["request"] = json.loads(item.pop("request_json"))
            item["result"] = json.loads(item.pop("result_json")) if item.get("result_json") else None
            item.pop("result_json", None)
        return item

    def list_analyses(self, tenant_id: str, limit: int = 50) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.cursor().execute(
                f"SELECT id,description,source_type,status,progress,cancel_requested,error,created_at,updated_at FROM analyses WHERE tenant_id={self.placeholder} ORDER BY sequence DESC LIMIT {self.placeholder}",
                (tenant_id, max(1, min(int(limit), 100))),
            ).fetchall()
        return [self._row(row) for row in rows]

    def record_analysis_feedback(
        self,
        tenant_id: str,
        analysis_id: str,
        user_id: str,
        *,
        rating: int,
        outcome: str,
        notes: str = "",
        feedback_source: str = "external",
        reason_code: str = "",
        expected_result: str = "",
        analysis_version: str = "unknown",
    ) -> dict[str, Any]:
        if int(rating) not in range(1, 6):
            raise ValueError("Rating must be between 1 and 5")
        if outcome not in FEEDBACK_OUTCOMES:
            raise ValueError("Unsupported feedback outcome")
        if feedback_source not in FEEDBACK_SOURCES:
            raise ValueError("Unsupported feedback source")
        normalized_reason = str(reason_code or "").strip()
        normalized_expected_result = str(expected_result or "").strip()
        if outcome == "correct" and not normalized_reason:
            normalized_reason = "no_issue"
        elif outcome != "correct" and not normalized_reason:
            raise ValueError("Partial or incorrect feedback requires a diagnostic reason")
        if normalized_reason not in FEEDBACK_REASON_CODES:
            raise ValueError("Unsupported feedback reason")
        if outcome == "correct":
            normalized_reason = "no_issue"
        elif normalized_reason == "no_issue":
            raise ValueError("Partial or incorrect feedback requires a diagnostic reason")
        if outcome != "correct" and not normalized_expected_result:
            raise ValueError("Partial or incorrect feedback requires the expected result")
        if self.get_analysis(tenant_id, analysis_id) is None:
            raise ValueError("Analysis not found")
        now, feedback_id = self._now(), uuid4().hex
        values = (
            feedback_id,
            tenant_id,
            analysis_id,
            user_id,
            int(rating),
            outcome,
            str(notes or "").strip()[:1000],
            feedback_source,
            "pending",
            None,
            None,
            "",
            normalized_reason,
            normalized_expected_result[:2000],
            str(analysis_version or "unknown").strip()[:128] or "unknown",
            "",
            now,
            now,
        )
        with self.connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                f"""INSERT INTO analysis_feedback(
                    id,tenant_id,analysis_id,user_id,rating,outcome,notes,feedback_source,
                    verification_status,verified_by,verified_at,reviewer_notes,reason_code,
                    expected_result,analysis_version,issue_reference,created_at,updated_at
                ) VALUES ({','.join([self.placeholder] * 18)})
                ON CONFLICT(tenant_id,analysis_id,user_id) DO UPDATE SET
                    rating=excluded.rating,outcome=excluded.outcome,notes=excluded.notes,
                    feedback_source=excluded.feedback_source,verification_status='pending',
                    verified_by=NULL,verified_at=NULL,reviewer_notes='',
                    reason_code=excluded.reason_code,expected_result=excluded.expected_result,
                    analysis_version=excluded.analysis_version,issue_reference='',
                    updated_at=excluded.updated_at""",
                values,
            )
            row = cursor.execute(
                f"SELECT * FROM analysis_feedback WHERE tenant_id={self.placeholder} AND analysis_id={self.placeholder} AND user_id={self.placeholder}",
                (tenant_id, analysis_id, user_id),
            ).fetchone()
        return self._row(row)

    def get_analysis_feedback(
        self, tenant_id: str, analysis_id: str, user_id: str
    ) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.cursor().execute(
                f"SELECT * FROM analysis_feedback WHERE tenant_id={self.placeholder} AND analysis_id={self.placeholder} AND user_id={self.placeholder}",
                (tenant_id, analysis_id, user_id),
            ).fetchone()
        return self._row(row)

    def list_analysis_feedback(
        self,
        tenant_id: str,
        *,
        verification_status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        clauses = [f"f.tenant_id={self.placeholder}"]
        params: list[Any] = [tenant_id]
        if verification_status:
            if verification_status not in FEEDBACK_VERIFICATION_STATUSES:
                raise ValueError("Unsupported verification status")
            clauses.append(f"f.verification_status={self.placeholder}")
            params.append(verification_status)
        params.append(max(1, min(int(limit), 200)))
        with self.connect() as connection:
            rows = connection.cursor().execute(
                f"""SELECT f.*, u.email AS user_email, a.description AS analysis_description
                    FROM analysis_feedback f
                    JOIN users u ON u.id=f.user_id AND u.tenant_id=f.tenant_id
                    JOIN analyses a ON a.id=f.analysis_id AND a.tenant_id=f.tenant_id
                    WHERE {' AND '.join(clauses)}
                    ORDER BY f.sequence DESC LIMIT {self.placeholder}""",
                tuple(params),
            ).fetchall()
        return [self._row(row) for row in rows]

    def review_analysis_feedback(
        self,
        tenant_id: str,
        feedback_id: str,
        reviewer_id: str,
        *,
        verification_status: str,
        reviewer_notes: str = "",
        issue_reference: str = "",
    ) -> dict[str, Any]:
        if verification_status not in {"verified", "rejected"}:
            raise ValueError("Review status must be verified or rejected")
        with self.connect() as connection:
            cursor = connection.cursor()
            existing = cursor.execute(
                f"SELECT * FROM analysis_feedback WHERE tenant_id={self.placeholder} AND id={self.placeholder}",
                (tenant_id, feedback_id),
            ).fetchone()
            feedback = self._row(existing)
            if feedback is None:
                raise ValueError("Feedback not found")
            if feedback["user_id"] == reviewer_id:
                raise ValueError("A feedback author cannot verify their own evidence")
            reviewed_at = self._now()
            cursor.execute(
                f"""UPDATE analysis_feedback SET verification_status={self.placeholder},
                    verified_by={self.placeholder},verified_at={self.placeholder},
                    reviewer_notes={self.placeholder},issue_reference={self.placeholder},
                    updated_at={self.placeholder}
                    WHERE tenant_id={self.placeholder} AND id={self.placeholder}""",
                (
                    verification_status,
                    reviewer_id,
                    reviewed_at,
                    str(reviewer_notes or "").strip()[:1000],
                    str(issue_reference or "").strip()[:255],
                    reviewed_at,
                    tenant_id,
                    feedback_id,
                ),
            )
            row = cursor.execute(
                f"SELECT * FROM analysis_feedback WHERE tenant_id={self.placeholder} AND id={self.placeholder}",
                (tenant_id, feedback_id),
            ).fetchone()
        return self._row(row)

    def feedback_summary(self, tenant_id: str | None = None) -> dict[str, Any]:
        where, params = "", ()
        if tenant_id:
            where, params = f" WHERE tenant_id={self.placeholder}", (tenant_id,)
        verified_clause = "feedback_source='external' AND verification_status='verified'"
        verified_where = f" WHERE {verified_clause}"
        if tenant_id:
            verified_where += f" AND tenant_id={self.placeholder}"
        with self.connect() as connection:
            cursor = connection.cursor()
            aggregate = cursor.execute(
                f"SELECT COUNT(*) AS total, AVG(rating) AS average_rating FROM analysis_feedback{where}",
                params,
            ).fetchone()
            outcomes = cursor.execute(
                f"SELECT outcome, COUNT(*) AS total FROM analysis_feedback{where} GROUP BY outcome",
                params,
            ).fetchall()
            verification = cursor.execute(
                f"SELECT verification_status, COUNT(*) AS total FROM analysis_feedback{where} GROUP BY verification_status",
                params,
            ).fetchall()
            sources = cursor.execute(
                f"SELECT feedback_source, COUNT(*) AS total FROM analysis_feedback{where} GROUP BY feedback_source",
                params,
            ).fetchall()
            reasons = cursor.execute(
                f"SELECT reason_code, COUNT(*) AS total FROM analysis_feedback{where} GROUP BY reason_code",
                params,
            ).fetchall()
            verified_aggregate = cursor.execute(
                f"""SELECT COUNT(*) AS total, AVG(rating) AS average_rating,
                    COUNT(DISTINCT user_id) AS distinct_testers
                    FROM analysis_feedback{verified_where}""",
                params,
            ).fetchone()
            verified_outcomes = cursor.execute(
                f"""SELECT outcome, COUNT(*) AS total FROM analysis_feedback{verified_where}
                    GROUP BY outcome""",
                params,
            ).fetchall()
        aggregate_item = self._row(aggregate) or {}
        verified_item = self._row(verified_aggregate) or {}
        normalized_outcomes = {
            str(item["outcome"]): int(item["total"])
            for item in (self._row(row) for row in outcomes)
        }
        normalized_verified = {
            str(item["outcome"]): int(item["total"])
            for item in (self._row(row) for row in verified_outcomes)
        }
        verified_total = int(verified_item.get("total") or 0)
        verified_correct = int(normalized_verified.get("correct", 0))
        return {
            "total": int(aggregate_item.get("total") or 0),
            "average_rating": round(float(aggregate_item.get("average_rating") or 0.0), 2),
            "outcomes": normalized_outcomes,
            "verification_statuses": {
                str(item["verification_status"]): int(item["total"])
                for item in (self._row(row) for row in verification)
            },
            "sources": {
                str(item["feedback_source"]): int(item["total"])
                for item in (self._row(row) for row in sources)
            },
            "reason_codes": {
                str(item["reason_code"]): int(item["total"])
                for item in (self._row(row) for row in reasons)
            },
            "verified_external_total": verified_total,
            "verified_external_correct": verified_correct,
            "verified_external_partial": int(normalized_verified.get("partial", 0)),
            "verified_external_incorrect": int(normalized_verified.get("incorrect", 0)),
            "verified_external_outcomes": normalized_verified,
            "verified_external_average_rating": round(
                float(verified_item.get("average_rating") or 0.0), 2
            ),
            "verified_external_accuracy": round(
                verified_correct / verified_total if verified_total else 0.0, 4
            ),
            "distinct_external_testers": int(verified_item.get("distinct_testers") or 0),
        }

    def record_beta_funnel_event(
        self,
        tenant_id: str,
        user_id: str,
        session_id: str,
        event_type: str,
        analysis_id: str = "",
    ) -> bool:
        if event_type not in BETA_FUNNEL_EVENTS:
            raise ValueError("Unsupported beta funnel event")
        normalized_session = str(session_id or "").strip()[:128]
        if not normalized_session:
            raise ValueError("Beta session id is required")
        normalized_analysis = str(analysis_id or "").strip()[:64]
        with self.connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                f"""INSERT INTO beta_funnel_events(
                    id,tenant_id,user_id,session_id,event_type,analysis_id,created_at
                ) VALUES ({','.join([self.placeholder] * 7)})
                ON CONFLICT(tenant_id,session_id,event_type,analysis_id) DO NOTHING""",
                (
                    uuid4().hex,
                    tenant_id,
                    user_id,
                    normalized_session,
                    event_type,
                    normalized_analysis,
                    self._now(),
                ),
            )
            return cursor.rowcount == 1

    def record_beta_analysis_completed(
        self, tenant_id: str, user_id: str, analysis_id: str
    ) -> bool:
        with self.connect() as connection:
            row = connection.cursor().execute(
                f"""SELECT session_id FROM beta_funnel_events
                    WHERE tenant_id={self.placeholder} AND user_id={self.placeholder}
                    AND analysis_id={self.placeholder} AND event_type='analysis_started'
                    ORDER BY sequence DESC LIMIT 1""",
                (tenant_id, user_id, analysis_id),
            ).fetchone()
        item = self._row(row)
        if item is None:
            return False
        return self.record_beta_funnel_event(
            tenant_id,
            user_id,
            item["session_id"],
            "analysis_completed",
            analysis_id,
        )

    def beta_funnel_summary(self, tenant_id: str | None = None) -> dict[str, Any]:
        where, params = "", ()
        if tenant_id:
            where, params = f" WHERE tenant_id={self.placeholder}", (tenant_id,)
        with self.connect() as connection:
            rows = connection.cursor().execute(
                f"""SELECT event_type, COUNT(*) AS events,
                    COUNT(DISTINCT session_id) AS sessions,
                    COUNT(DISTINCT user_id) AS users
                    FROM beta_funnel_events{where} GROUP BY event_type""",
                params,
            ).fetchall()
        observed = {item["event_type"]: item for item in (self._row(row) for row in rows)}
        stages = {
            event: {
                "events": int((observed.get(event) or {}).get("events") or 0),
                "sessions": int((observed.get(event) or {}).get("sessions") or 0),
                "users": int((observed.get(event) or {}).get("users") or 0),
            }
            for event in BETA_FUNNEL_ORDER
        }

        def conversion(numerator: str, denominator: str) -> float:
            base = stages[denominator]["sessions"]
            return round(stages[numerator]["sessions"] / base, 4) if base else 0.0

        return {
            "stages": stages,
            "conversion": {
                "started_to_completed": conversion("analysis_completed", "analysis_started"),
                "completed_to_result_viewed": conversion("result_viewed", "analysis_completed"),
                "result_viewed_to_feedback": conversion("feedback_submitted", "result_viewed"),
            },
        }

    def record_quality_snapshot(self, tenant_id: str, payload: dict[str, Any]) -> str:
        snapshot_id=uuid4().hex
        with self.connect() as connection:
            connection.cursor().execute(
                f"INSERT INTO quality_snapshots(id,tenant_id,payload_json,created_at) VALUES ({','.join([self.placeholder]*4)})",
                (snapshot_id,tenant_id,json.dumps(payload,ensure_ascii=False,default=str),self._now()),
            )
        return snapshot_id

    def list_quality_snapshots(self, tenant_id: str, limit: int=20) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows=connection.cursor().execute(
                f"SELECT id,payload_json,created_at FROM quality_snapshots WHERE tenant_id={self.placeholder} ORDER BY sequence DESC LIMIT {self.placeholder}",
                (tenant_id,max(1,min(int(limit),100))),
            ).fetchall()
        result=[]
        for row in rows:
            item=self._row(row); item["payload"]=json.loads(item.pop("payload_json")); result.append(item)
        return result

    def analysis_status_summary(self) -> dict[str, int]:
        with self.connect() as connection:
            rows = connection.cursor().execute(
                "SELECT status, COUNT(*) AS total FROM analyses GROUP BY status"
            ).fetchall()
        normalized = [self._row(row) for row in rows]
        return {str(row["status"]): int(row["total"]) for row in normalized}

    def delete_analysis(self, tenant_id: str, analysis_id: str) -> bool:
        with self.connect() as connection:
            cursor = connection.cursor()
            cursor.execute(f"DELETE FROM analysis_feedback WHERE tenant_id={self.placeholder} AND analysis_id={self.placeholder}", (tenant_id, analysis_id))
            cursor.execute(f"DELETE FROM beta_funnel_events WHERE tenant_id={self.placeholder} AND analysis_id={self.placeholder}", (tenant_id, analysis_id))
            cursor.execute(f"DELETE FROM analyses WHERE tenant_id={self.placeholder} AND id={self.placeholder}", (tenant_id, analysis_id))
            return cursor.rowcount == 1

    def retention_candidates(self, before: str, tenant_id: str | None = None) -> list[dict[str, Any]]:
        clauses = [f"created_at < {self.placeholder}", "status IN ('completed','failed','cancelled')"]
        params: list[Any] = [before]
        if tenant_id:
            clauses.append(f"tenant_id={self.placeholder}")
            params.append(tenant_id)
        with self.connect() as connection:
            rows = connection.cursor().execute(
                f"SELECT id,tenant_id,status,created_at FROM analyses WHERE {' AND '.join(clauses)} ORDER BY created_at", tuple(params)
            ).fetchall()
        return [self._row(row) for row in rows]

    def purge_analyses_before(self, before: str, tenant_id: str | None = None) -> int:
        return sum(self.delete_analysis(item["tenant_id"], item["id"]) for item in self.retention_candidates(before, tenant_id))

    def backup(self, destination: str | Path) -> Path:
        if self.backend != "sqlite":
            raise RuntimeError("PostgreSQL backups must use pg_dump")
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.sqlite_path) as source, sqlite3.connect(target) as backup:
            source.backup(backup)
        return target

    def restore(self, source: str | Path) -> Path:
        if self.backend != "sqlite":
            raise RuntimeError("PostgreSQL restores must use pg_restore")
        backup_path = Path(source)
        if not backup_path.is_file():
            raise ValueError("Backup file does not exist")
        with sqlite3.connect(backup_path) as backup, sqlite3.connect(self.sqlite_path) as destination:
            backup.backup(destination)
        return self.sqlite_path

    def readiness(self) -> dict[str, Any]:
        with self.connect() as connection:
            row = connection.cursor().execute("SELECT MAX(version) AS version FROM schema_migrations").fetchone()
            version = row.get("version") if isinstance(row, dict) else row[0]
        return {"status": "ready", "backend": self.backend, "schema_version": version}

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _row(row) -> dict[str, Any] | None:
        return dict(row) if row is not None else None

    def _ensure_column(self, cursor, table: str, column: str, definition: str) -> None:
        if self.backend == "sqlite":
            columns = {row[1] for row in cursor.execute(f"PRAGMA table_info({table})").fetchall()}
        else:
            rows = cursor.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name=%s",
                (table,),
            ).fetchall()
            columns = {row.get("column_name") if isinstance(row, dict) else row[0] for row in rows}
        if column not in columns:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
