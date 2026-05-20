from __future__ import annotations

from pathlib import Path

from app.db.sqlite import get_connection

_USER_DATA_TABLES = [
    "lexemes",
    "sentence_bank",
    "phrase_translations",
    "ignored_tokens",
    "wordbank_background_jobs",
    "token_events",
    "typo_feedback",
    "verification_change_log",
]


def clear_user_learning_data(db_path: Path, owner_user_id: int, *, include_search_usage: bool = False) -> None:
    tables = [*_USER_DATA_TABLES]
    if include_search_usage:
        tables.append("user_search_usage")
    with get_connection(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        for table in tables:
            conn.execute(f"DELETE FROM {table} WHERE owner_user_id = ?", (owner_user_id,))  # noqa: S608
