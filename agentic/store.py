"""SQLite persistence for memories, runs, events, chat sessions, and schedules.

One file, standard library only. Memory search uses FTS5 with BM25 ranking
when the SQLite build supports it and falls back to keyword LIKE matching.
"""

from __future__ import annotations

import json
import re
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any

WORD = re.compile(r"\w{2,}", re.UNICODE)

SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT 'user',
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    goal TEXT NOT NULL,
    mode TEXT NOT NULL,
    origin TEXT NOT NULL DEFAULT 'cli',
    status TEXT NOT NULL,
    result TEXT,
    created_at REAL NOT NULL,
    finished_at REAL
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    ts REAL NOT NULL,
    type TEXT NOT NULL,
    agent TEXT,
    data TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS events_run ON events(run_id, id);
CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    ts REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS chat_session ON chat_messages(session, id);
CREATE TABLE IF NOT EXISTS schedules (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    goal TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'agent',
    head TEXT NOT NULL DEFAULT 'assistant',
    interval_seconds INTEGER,
    cron TEXT,
    notify TEXT,
    enabled INTEGER NOT NULL DEFAULT 1,
    next_run REAL NOT NULL,
    last_run REAL,
    last_status TEXT,
    created_at REAL NOT NULL
);
"""


class Store:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        if str(path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        with self._lock:
            self._db.executescript(SCHEMA)
            self._db.execute("PRAGMA journal_mode=WAL")
            self.fts = self._enable_fts()
            self._db.commit()

    def _enable_fts(self) -> bool:
        try:
            self._db.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts "
                "USING fts5(text, tags, content='memories', content_rowid='id')"
            )
            self._db.executescript(
                """
                CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                  INSERT INTO memories_fts(rowid, text, tags) VALUES (new.id, new.text, new.tags);
                END;
                CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
                  INSERT INTO memories_fts(memories_fts, rowid, text, tags)
                  VALUES ('delete', old.id, old.text, old.tags);
                END;
                """
            )
            return True
        except sqlite3.OperationalError:
            return False

    def close(self) -> None:
        with self._lock:
            self._db.close()

    def _execute(self, sql: str, params: tuple | dict = ()) -> sqlite3.Cursor:
        with self._lock:
            cursor = self._db.execute(sql, params)
            self._db.commit()
            return cursor

    def _query(self, sql: str, params: tuple | dict = ()) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(row) for row in self._db.execute(sql, params).fetchall()]

    # Memories -------------------------------------------------------------

    def add_memory(self, text: str, tags: list[str] | None = None, source: str = "user") -> int:
        text = text.strip()[:4_000]
        if not text:
            raise ValueError("memory text must not be empty")
        existing = self._query("SELECT id FROM memories WHERE text = ? LIMIT 1", (text,))
        if existing:
            return int(existing[0]["id"])
        cursor = self._execute(
            "INSERT INTO memories(text, tags, source, created_at) VALUES (?, ?, ?, ?)",
            (text, " ".join(tags or []), source, time.time()),
        )
        return int(cursor.lastrowid)

    def search_memories(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        words = WORD.findall(query.casefold())[:12]
        if not words:
            return self._query("SELECT * FROM memories ORDER BY id DESC LIMIT ?", (limit,))
        if self.fts:
            match = " OR ".join(f'"{word}"' for word in words)
            return self._query(
                "SELECT m.* FROM memories_fts f JOIN memories m ON m.id = f.rowid "
                "WHERE memories_fts MATCH ? ORDER BY bm25(memories_fts) LIMIT ?",
                (match, limit),
            )
        clauses = " OR ".join("lower(text) LIKE ?" for _ in words)
        return self._query(
            f"SELECT * FROM memories WHERE {clauses} ORDER BY id DESC LIMIT ?",
            (*[f"%{word}%" for word in words], limit),
        )

    def list_memories(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._query("SELECT * FROM memories ORDER BY id DESC LIMIT ?", (limit,))

    def delete_memory(self, memory_id: int) -> bool:
        return self._execute("DELETE FROM memories WHERE id = ?", (memory_id,)).rowcount > 0

    # Runs and events ------------------------------------------------------

    def create_run(self, goal: str, mode: str, origin: str = "cli") -> str:
        run_id = uuid.uuid4().hex[:12]
        self._execute(
            "INSERT INTO runs(id, goal, mode, origin, status, created_at) "
            "VALUES (?, ?, ?, ?, 'running', ?)",
            (run_id, goal, mode, origin, time.time()),
        )
        return run_id

    def finish_run(self, run_id: str, status: str, result: str) -> None:
        self._execute(
            "UPDATE runs SET status = ?, result = ?, finished_at = ? WHERE id = ?",
            (status, result, time.time(), run_id),
        )

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        rows = self._query("SELECT * FROM runs WHERE id = ?", (run_id,))
        return rows[0] if rows else None

    def list_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._query("SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,))

    def add_event(self, run_id: str, ts: float, kind: str, agent: str | None, data: dict) -> int:
        cursor = self._execute(
            "INSERT INTO events(run_id, ts, type, agent, data) VALUES (?, ?, ?, ?, ?)",
            (run_id, ts, kind, agent, json.dumps(data, default=str)),
        )
        return int(cursor.lastrowid)

    def events(self, run_id: str, after_id: int = 0) -> list[dict[str, Any]]:
        rows = self._query(
            "SELECT * FROM events WHERE run_id = ? AND id > ? ORDER BY id", (run_id, after_id)
        )
        for row in rows:
            row["data"] = json.loads(row["data"])
        return rows

    # Chat sessions --------------------------------------------------------

    def add_chat_message(self, session: str, role: str, content: str) -> None:
        self._execute(
            "INSERT INTO chat_messages(session, role, content, ts) VALUES (?, ?, ?, ?)",
            (session, role, content, time.time()),
        )

    def chat_history(self, session: str, limit: int = 12) -> list[dict[str, Any]]:
        rows = self._query(
            "SELECT role, content FROM chat_messages WHERE session = ? ORDER BY id DESC LIMIT ?",
            (session, limit),
        )
        return list(reversed(rows))

    def clear_chat(self, session: str) -> None:
        self._execute("DELETE FROM chat_messages WHERE session = ?", (session,))

    # Schedules ------------------------------------------------------------

    def add_schedule(self, **fields: Any) -> str:
        schedule_id = uuid.uuid4().hex[:8]
        fields = {"id": schedule_id, "created_at": time.time(), **fields}
        columns = ", ".join(fields)
        placeholders = ", ".join(f":{key}" for key in fields)
        self._execute(f"INSERT INTO schedules({columns}) VALUES ({placeholders})", fields)
        return schedule_id

    def list_schedules(self) -> list[dict[str, Any]]:
        return self._query("SELECT * FROM schedules ORDER BY created_at")

    def due_schedules(self, now: float) -> list[dict[str, Any]]:
        return self._query(
            "SELECT * FROM schedules WHERE enabled = 1 AND next_run <= ? ORDER BY next_run", (now,)
        )

    def update_schedule(self, schedule_id: str, **fields: Any) -> None:
        assignments = ", ".join(f"{key} = :{key}" for key in fields)
        self._execute(
            f"UPDATE schedules SET {assignments} WHERE id = :id", {**fields, "id": schedule_id}
        )

    def delete_schedule(self, schedule_id: str) -> bool:
        return self._execute("DELETE FROM schedules WHERE id = ?", (schedule_id,)).rowcount > 0
