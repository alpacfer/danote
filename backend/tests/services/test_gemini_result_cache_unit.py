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


def test_gemini_result_cache_close_works_with_multiple_threads(tmp_path) -> None:
    import threading
    cache = GeminiResultCache(tmp_path / "gemini.sqlite")

    errors: list[Exception] = []

    def worker():
        try:
            cache.put("thread_key", "thread_value")
            # Verify we can read it
            assert cache.get("thread_key") == "thread_value"
        except Exception as e:
            errors.append(e)

    # Spawn thread to open its connection
    t = threading.Thread(target=worker)
    t.start()
    t.join()

    assert not errors

    # Now close the cache from the main thread
    cache.close()

    # Verify that calling put/get from a thread (e.g. background or main)
    # does NOT crash with ProgrammingError (closed database), but rather
    # re-opens a clean connection.
    def post_close_worker():
        try:
            cache.put("new_key", "new_value")
            assert cache.get("new_key") == "new_value"
        except Exception as e:
            errors.append(e)

    t2 = threading.Thread(target=post_close_worker)
    t2.start()
    t2.join()

    assert not errors

