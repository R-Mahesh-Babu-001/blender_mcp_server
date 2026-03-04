from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


@dataclass(slots=True)
class JobRecord:
    job_id: str
    prompt: str
    status: str
    image_path: str | None
    result_path: str | None
    error: str | None
    created_at: datetime
    updated_at: datetime


class JobRepository:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    prompt TEXT NOT NULL,
                    status TEXT NOT NULL,
                    image_path TEXT,
                    result_path TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                );
                """
            )

    def create_job(self, job_id: str, prompt: str, image_path: str | None) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO jobs (job_id, prompt, status, image_path, result_path, error, created_at, updated_at)
                VALUES (?, ?, 'queued', ?, NULL, NULL, ?, ?)
                """,
                (job_id, prompt, image_path, now, now),
            )

    def update_job(
        self,
        job_id: str,
        *,
        status: str | None = None,
        result_path: str | None = None,
        error: str | None = None,
    ) -> None:
        updates: list[str] = []
        values: list[str | None] = []
        if status is not None:
            updates.append("status = ?")
            values.append(status)
        if result_path is not None:
            updates.append("result_path = ?")
            values.append(result_path)
        if error is not None:
            updates.append("error = ?")
            values.append(error)
        updates.append("updated_at = ?")
        values.append(datetime.now(timezone.utc).isoformat())
        values.append(job_id)
        with self._connect() as conn:
            conn.execute(f"UPDATE jobs SET {', '.join(updates)} WHERE job_id = ?", values)

    def get_job(self, job_id: str) -> JobRecord | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        if not row:
            return None
        return JobRecord(
            job_id=row["job_id"],
            prompt=row["prompt"],
            status=row["status"],
            image_path=row["image_path"],
            result_path=row["result_path"],
            error=row["error"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def add_event(self, job_id: str, event_type: str, payload: dict) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO events (job_id, type, payload, timestamp) VALUES (?, ?, ?, ?)",
                (
                    job_id,
                    event_type,
                    json.dumps(payload),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def list_events(self, job_id: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT type, payload, timestamp FROM events WHERE job_id = ? ORDER BY id ASC",
                (job_id,),
            ).fetchall()
        return [
            {
                "type": row["type"],
                "payload": json.loads(row["payload"]),
                "timestamp": row["timestamp"],
            }
            for row in rows
        ]
