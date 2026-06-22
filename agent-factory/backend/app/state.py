from __future__ import annotations

import asyncio
import json
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AgentEvent:
    timestamp: datetime
    agent: str
    phase: str
    level: str
    message: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class JobRecord:
    job_id: str
    prompt: str
    business_requirements: str
    created_at: datetime
    updated_at: datetime
    status: str
    uploaded_files: list[str] = field(default_factory=list)
    file_paths: list[Path] = field(default_factory=list)
    clarification_questions: list[str] = field(default_factory=list)
    clarification_answers: dict[str, str] = field(default_factory=dict)
    artifacts: dict[str, Any] = field(default_factory=dict)
    events: list[AgentEvent] = field(default_factory=list)


class JobStore:
    def __init__(self, db_path: Path | None = None) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._subscribers: dict[str, list[asyncio.Queue[dict[str, Any]]]] = {}
        self._lock = asyncio.Lock()
        default_path = Path(__file__).resolve().parent.parent / "data" / "agent_memory.db"
        self._db_path = db_path or default_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_db()
        self._load_jobs_from_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    prompt TEXT NOT NULL,
                    business_requirements TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    uploaded_files_json TEXT NOT NULL,
                    file_paths_json TEXT NOT NULL,
                    clarification_questions_json TEXT NOT NULL,
                    clarification_answers_json TEXT NOT NULL,
                    artifacts_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    agent TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS learning_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    tags_json TEXT NOT NULL,
                    recommendations_json TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    score REAL NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_job_id ON events(job_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_learning_created_at ON learning_entries(created_at)")

    @staticmethod
    def _json_dumps(data: Any) -> str:
        return json.dumps(data, ensure_ascii=True, default=str)

    @staticmethod
    def _json_loads(value: str | None, fallback: Any) -> Any:
        if not value:
            return fallback
        try:
            return json.loads(value)
        except Exception:  # noqa: BLE001
            return fallback

    def _save_job_nolock(self, job: JobRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO jobs (
                    job_id, prompt, business_requirements, created_at, updated_at, status,
                    uploaded_files_json, file_paths_json, clarification_questions_json,
                    clarification_answers_json, artifacts_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    prompt=excluded.prompt,
                    business_requirements=excluded.business_requirements,
                    created_at=excluded.created_at,
                    updated_at=excluded.updated_at,
                    status=excluded.status,
                    uploaded_files_json=excluded.uploaded_files_json,
                    file_paths_json=excluded.file_paths_json,
                    clarification_questions_json=excluded.clarification_questions_json,
                    clarification_answers_json=excluded.clarification_answers_json,
                    artifacts_json=excluded.artifacts_json
                """,
                (
                    job.job_id,
                    job.prompt,
                    job.business_requirements,
                    job.created_at.isoformat(),
                    job.updated_at.isoformat(),
                    job.status,
                    self._json_dumps(job.uploaded_files),
                    self._json_dumps([str(path) for path in job.file_paths]),
                    self._json_dumps(job.clarification_questions),
                    self._json_dumps(job.clarification_answers),
                    self._json_dumps(job.artifacts),
                ),
            )

    def _save_event_nolock(self, job_id: str, event: AgentEvent) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO events (job_id, timestamp, agent, phase, level, message, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    event.timestamp.isoformat(),
                    event.agent,
                    event.phase,
                    event.level,
                    event.message,
                    self._json_dumps(event.payload),
                ),
            )

    def _load_jobs_from_db(self) -> None:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM jobs").fetchall()
            for row in rows:
                file_paths = [Path(item) for item in self._json_loads(row["file_paths_json"], [])]
                job = JobRecord(
                    job_id=row["job_id"],
                    prompt=row["prompt"],
                    business_requirements=row["business_requirements"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                    status=row["status"],
                    uploaded_files=self._json_loads(row["uploaded_files_json"], []),
                    file_paths=file_paths,
                    clarification_questions=self._json_loads(row["clarification_questions_json"], []),
                    clarification_answers=self._json_loads(row["clarification_answers_json"], {}),
                    artifacts=self._json_loads(row["artifacts_json"], {}),
                )
                self._jobs[job.job_id] = job
                self._subscribers[job.job_id] = []

            event_rows = conn.execute("SELECT * FROM events ORDER BY id ASC").fetchall()
            for row in event_rows:
                job = self._jobs.get(row["job_id"])
                if not job:
                    continue
                event = AgentEvent(
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    agent=row["agent"],
                    phase=row["phase"],
                    level=row["level"],
                    message=row["message"],
                    payload=self._json_loads(row["payload_json"], {}),
                )
                job.events.append(event)
                if len(job.events) > 500:
                    job.events = job.events[-500:]

    async def create_job(self, prompt: str, business_requirements: str, uploaded_files: list[str], file_paths: list[Path]) -> JobRecord:
        async with self._lock:
            job_id = uuid4().hex
            now = utcnow()
            job = JobRecord(
                job_id=job_id,
                prompt=prompt,
                business_requirements=business_requirements,
                created_at=now,
                updated_at=now,
                status="intake",
                uploaded_files=uploaded_files,
                file_paths=file_paths,
            )
            self._jobs[job_id] = job
            self._subscribers[job_id] = []
            self._save_job_nolock(job)
            return job

    async def get_job(self, job_id: str) -> JobRecord | None:
        async with self._lock:
            return self._jobs.get(job_id)

    async def set_status(self, job_id: str, status: str) -> None:
        async with self._lock:
            job = self._jobs[job_id]
            job.status = status
            job.updated_at = utcnow()
            self._save_job_nolock(job)

    async def set_questions(self, job_id: str, questions: list[str]) -> None:
        async with self._lock:
            job = self._jobs[job_id]
            job.clarification_questions = questions
            job.updated_at = utcnow()
            self._save_job_nolock(job)

    async def set_uploaded_files(self, job_id: str, uploaded_files: list[str], file_paths: list[Path]) -> None:
        async with self._lock:
            job = self._jobs[job_id]
            job.uploaded_files = uploaded_files
            job.file_paths = file_paths
            job.updated_at = utcnow()
            self._save_job_nolock(job)

    async def set_business_requirements(self, job_id: str, business_requirements: str) -> None:
        async with self._lock:
            job = self._jobs[job_id]
            job.business_requirements = business_requirements
            job.updated_at = utcnow()
            self._save_job_nolock(job)

    async def set_answers(self, job_id: str, answers: dict[str, str]) -> None:
        async with self._lock:
            job = self._jobs[job_id]
            job.clarification_answers = answers
            job.updated_at = utcnow()
            self._save_job_nolock(job)

    async def merge_artifacts(self, job_id: str, artifacts: dict[str, Any]) -> None:
        async with self._lock:
            job = self._jobs[job_id]
            job.artifacts.update(artifacts)
            job.updated_at = utcnow()
            self._save_job_nolock(job)

    async def append_event(self, job_id: str, agent: str, phase: str, level: str, message: str, payload: dict[str, Any] | None = None) -> None:
        payload = payload or {}
        event = AgentEvent(
            timestamp=utcnow(),
            agent=agent,
            phase=phase,
            level=level,
            message=message,
            payload=payload,
        )
        async with self._lock:
            job = self._jobs[job_id]
            job.events.append(event)
            job.updated_at = utcnow()
            if len(job.events) > 500:
                job.events = job.events[-500:]
            self._save_job_nolock(job)
            self._save_event_nolock(job_id, event)
            subscribers = list(self._subscribers.get(job_id, []))

        message_obj = {
            "type": "event",
            "data": {
                "timestamp": event.timestamp.isoformat(),
                "agent": event.agent,
                "phase": event.phase,
                "level": event.level,
                "message": event.message,
                "payload": event.payload,
            },
        }
        for queue in subscribers:
            await queue.put(message_obj)

    async def subscribe(self, job_id: str) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        async with self._lock:
            self._subscribers.setdefault(job_id, []).append(queue)
        return queue

    async def unsubscribe(self, job_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        async with self._lock:
            items = self._subscribers.get(job_id)
            if not items:
                return
            if queue in items:
                items.remove(queue)

    async def snapshot(self, job_id: str) -> dict[str, Any] | None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            return {
                "job_id": job.job_id,
                "status": job.status,
                "created_at": job.created_at.isoformat(),
                "updated_at": job.updated_at.isoformat(),
                "prompt": job.prompt,
                "business_requirements": job.business_requirements,
                "uploaded_files": job.uploaded_files,
                "clarification_questions": job.clarification_questions,
                "clarification_answers": job.clarification_answers,
                "artifacts": job.artifacts,
                "events": [
                    {
                        "timestamp": e.timestamp.isoformat(),
                        "agent": e.agent,
                        "phase": e.phase,
                        "level": e.level,
                        "message": e.message,
                        "payload": e.payload,
                    }
                    for e in job.events
                ],
            }

    async def record_learning(
        self,
        job_id: str,
        tags: list[str],
        recommendations: list[str],
        outcome: str,
        score: float,
    ) -> None:
        created_at = utcnow().isoformat()
        async with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO learning_entries (job_id, created_at, tags_json, recommendations_json, outcome, score)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        job_id,
                        created_at,
                        self._json_dumps(tags),
                        self._json_dumps(recommendations),
                        outcome,
                        score,
                    ),
                )

    async def suggest_next_best_actions(self, prompt: str, business_requirements: str, max_items: int = 5) -> list[str]:
        query_tokens = self._tokenize(f"{prompt} {business_requirements}")
        async with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT created_at, tags_json, recommendations_json, score
                    FROM learning_entries
                    ORDER BY id DESC
                    LIMIT 200
                    """
                ).fetchall()

        ranked: list[tuple[float, str]] = []
        seen: set[str] = set()
        for row in rows:
            tags = self._json_loads(row["tags_json"], [])
            recommendations = self._json_loads(row["recommendations_json"], [])
            score = float(row["score"] or 0.0)
            tag_tokens = self._tokenize(" ".join(str(tag) for tag in tags))
            overlap = len(query_tokens.intersection(tag_tokens))
            base_weight = overlap * 2.0 + score

            for idx, recommendation in enumerate(recommendations):
                action = str(recommendation).strip()
                if not action:
                    continue
                lowered = action.lower()
                if lowered in seen:
                    continue
                seen.add(lowered)
                weight = base_weight + max(0.0, 1.0 - (idx * 0.1))
                ranked.append((weight, action))

        ranked.sort(key=lambda item: item[0], reverse=True)
        if ranked:
            return [item[1] for item in ranked[:max_items]]

        return [
            "Confermare outcome target e KPI misurabili prima dell'esecuzione.",
            "Eseguire un checkpoint intermedio con validazione dati e rischi.",
            "Formalizzare piano di iterazione con owner e scadenze.",
        ][:max_items]

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return {token for token in re.findall(r"[a-zA-Z0-9_]+", text.lower()) if len(token) > 2}
