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


SCHEMA_VERSION = 3


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
                notes TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                UNIQUE(tenant_id, analysis_id, user_id),
                FOREIGN KEY(tenant_id) REFERENCES tenants(id),
                FOREIGN KEY(analysis_id) REFERENCES analyses(id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )""")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_tenant_created ON analysis_feedback(tenant_id, created_at)")
            self._ensure_column(cursor, "analyses", "progress", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(cursor, "analyses", "cancel_requested", "INTEGER NOT NULL DEFAULT 0")
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
        persisted_request = {key: value for key, value in request.items() if key != "records"}
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

    def record_analysis_feedback(self, tenant_id: str, analysis_id: str, user_id: str, *, rating: int, outcome: str, notes: str = "") -> dict[str, Any]:
        if int(rating) not in range(1, 6):
            raise ValueError("Rating must be between 1 and 5")
        if outcome not in {"correct", "partial", "incorrect"}:
            raise ValueError("Unsupported feedback outcome")
        if self.get_analysis(tenant_id, analysis_id) is None:
            raise ValueError("Analysis not found")
        now, feedback_id = self._now(), uuid4().hex
        with self.connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                f"""INSERT INTO analysis_feedback(id,tenant_id,analysis_id,user_id,rating,outcome,notes,created_at,updated_at)
                VALUES ({','.join([self.placeholder] * 9)})
                ON CONFLICT(tenant_id,analysis_id,user_id) DO UPDATE SET
                    rating=excluded.rating,outcome=excluded.outcome,notes=excluded.notes,updated_at=excluded.updated_at""",
                (feedback_id, tenant_id, analysis_id, user_id, int(rating), outcome, str(notes or "").strip()[:1000], now, now),
            )
            row = cursor.execute(
                f"SELECT * FROM analysis_feedback WHERE tenant_id={self.placeholder} AND analysis_id={self.placeholder} AND user_id={self.placeholder}",
                (tenant_id, analysis_id, user_id),
            ).fetchone()
        return self._row(row)

    def feedback_summary(self, tenant_id: str | None = None) -> dict[str, Any]:
        where, params = "", ()
        if tenant_id:
            where, params = f" WHERE tenant_id={self.placeholder}", (tenant_id,)
        with self.connect() as connection:
            cursor = connection.cursor()
            aggregate = cursor.execute(f"SELECT COUNT(*) AS total, AVG(rating) AS average_rating FROM analysis_feedback{where}", params).fetchone()
            outcomes = cursor.execute(f"SELECT outcome, COUNT(*) AS total FROM analysis_feedback{where} GROUP BY outcome", params).fetchall()
        aggregate = self._row(aggregate) or {}
        normalized_outcomes = [self._row(row) for row in outcomes]
        return {
            "total": int(aggregate.get("total") or 0),
            "average_rating": round(float(aggregate.get("average_rating") or 0.0), 2),
            "outcomes": {str(row["outcome"]): int(row["total"]) for row in normalized_outcomes},
        }

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
