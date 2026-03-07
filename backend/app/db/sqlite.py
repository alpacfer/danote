from __future__ import annotations

import logging
import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)


def get_connection(db_path: Path, *, read_only: bool = False) -> sqlite3.Connection:
    if read_only:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    else:
        conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    if not read_only:
        try:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
        except sqlite3.DatabaseError:
            logger.debug("sqlite_runtime_pragmas_skipped", exc_info=True)
    return conn


@contextmanager
def timed_db_operation(operation: str) -> Iterator[None]:
    started_at = time.perf_counter()
    try:
        yield
    finally:
        logger.info(
            "sqlite_operation_timed",
            extra={
                "operation": operation,
                "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
            },
        )
