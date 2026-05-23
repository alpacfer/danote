from __future__ import annotations

import sqlite3
from pathlib import Path

from app.db.sqlite import get_connection
from app.services.use_cases.wordbank.categories import STARTER_WORD_CATEGORY_LABELS

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
        _reset_orphaned_word_categories(conn)


def _reset_orphaned_word_categories(conn: sqlite3.Connection) -> None:
    starter_rows = [
        (label, " ".join(label.strip().split()).casefold())
        for label in STARTER_WORD_CATEGORY_LABELS
    ]
    for label, normalized_label in starter_rows:
        conn.execute(
            """
            INSERT OR IGNORE INTO wordbank_categories (label, normalized_label)
            VALUES (?, ?)
            """,
            (label, normalized_label),
        )
        conn.execute(
            """
            UPDATE wordbank_categories
            SET label = ?, updated_at = CURRENT_TIMESTAMP
            WHERE normalized_label = ? AND label <> ?
            """,
            (label, normalized_label, label),
        )

    starter_keys = [normalized_label for _, normalized_label in starter_rows]
    placeholders = ",".join("?" for _ in starter_keys)
    conn.execute(
        f"""
        DELETE FROM wordbank_categories
        WHERE normalized_label NOT IN ({placeholders})
          AND NOT EXISTS (
              SELECT 1
              FROM wordbank_category_assignments wca
              WHERE wca.category_id = wordbank_categories.id
          )
        """,  # noqa: S608
        starter_keys,
    )
