from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path


class GeminiResultCache:
    """Tiny SQLite-backed string cache for deterministic Gemini calls."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._initialized = False
        self._local = threading.local()

    @property
    def path(self) -> Path:
        return self._path

    def _get_conn(self) -> sqlite3.Connection:
        self._ensure_initialized()
        if not hasattr(self._local, "conn"):
            conn = sqlite3.connect(self._path)
            try:
                conn.execute("PRAGMA journal_mode = WAL")
                conn.execute("PRAGMA synchronous = NORMAL")
            except sqlite3.DatabaseError:
                pass
            self._local.conn = conn
        return self._local.conn

    def get(self, key: str) -> str | None:
        conn = self._get_conn()
        with self._lock:
            row = conn.execute(
                "SELECT value FROM gemini_cache WHERE key = ?",
                (key,),
            ).fetchone()
        if row is None:
            return None
        value = row[0]
        return value if isinstance(value, str) else None

    def put(self, key: str, value: str) -> None:
        conn = self._get_conn()
        created_at = int(time.time())
        with self._lock:
            conn.execute(
                """
                INSERT INTO gemini_cache (key, value, created_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    created_at = excluded.created_at
                """,
                (key, value, created_at),
            )
            conn.commit()

    def clear(self) -> None:
        conn = self._get_conn()
        with self._lock:
            conn.execute("DELETE FROM gemini_cache")
            conn.commit()

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self._path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS gemini_cache (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        created_at INTEGER NOT NULL
                    )
                    """
                )
                conn.commit()
            self._initialized = True
