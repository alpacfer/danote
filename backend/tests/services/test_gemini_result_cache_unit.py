from __future__ import annotations

import sqlite3

import pytest

from app.services.gemini_result_cache import GeminiResultCache


def test_gemini_result_cache_close_releases_connections(tmp_path) -> None:
    cache = GeminiResultCache(tmp_path / "gemini.sqlite")

    cache.put("key", "value")
    conn = cache._get_conn()

    cache.close()

    assert cache._connections == {}
    with pytest.raises(sqlite3.ProgrammingError):
        conn.execute("SELECT 1")
