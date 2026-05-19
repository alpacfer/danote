from __future__ import annotations

from pathlib import Path

from app.api.schemas.v1.wordbank import ResetDatabaseResponse
from app.db.sqlite import get_connection
from app.services.use_cases.wordbank.runtime import WordbankRuntime

_USER_DATA_TABLES = [
    "lexemes",
    "sentence_bank",
    "phrase_translations",
    "ignored_tokens",
    "wordbank_background_jobs",
    "token_events",
    "typo_feedback",
    "verification_change_log",
    "user_search_usage",
]


def _clear_user_word_data(db_path: Path, owner_user_id: int) -> None:
    with get_connection(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        for table in _USER_DATA_TABLES:
            conn.execute(f"DELETE FROM {table} WHERE owner_user_id = ?", (owner_user_id,))  # noqa: S608


def reset_database(runtime: WordbankRuntime) -> ResetDatabaseResponse:
    _clear_user_word_data(runtime.db_path, runtime.owner_user_id)
    runtime.nlp.invalidate_typo_cache()
    return ResetDatabaseResponse(
        status="reset",
        message="Database reset complete.",
    )
