from __future__ import annotations

import json
from pathlib import Path

from app.db.repositories.wordbank_models import (
    VerificationChangeLogRecord,
    verification_change_log_from_row,
)
from app.db.sqlite import get_connection, timed_db_operation


class WordbankChangeLogRepository:
    _db_path: Path

    def insert_change_log_entry(
        self,
        *,
        stored_lemma: str,
        stored_surface_form: str | None,
        meaning_id: int | None,
        action_type: str,
        before_json: dict,
        after_json: dict,
        applied_at: str,
        provider: str | None,
    ) -> int:
        with timed_db_operation("wordbank.insert_change_log_entry"), get_connection(self._db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO verification_change_log
                    (stored_lemma, stored_surface_form, meaning_id, action_type,
                     before_json, after_json, applied_at, provider)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    stored_lemma,
                    stored_surface_form,
                    meaning_id,
                    action_type,
                    json.dumps(before_json, ensure_ascii=True, sort_keys=True),
                    json.dumps(after_json, ensure_ascii=True, sort_keys=True),
                    applied_at,
                    provider,
                ),
            )
            assert cursor.lastrowid is not None
            return int(cursor.lastrowid)

    def get_change_log_entries_for_lemma(
        self,
        stored_lemma: str,
        *,
        limit: int = 50,
    ) -> list[VerificationChangeLogRecord]:
        with timed_db_operation("wordbank.get_change_log_entries_for_lemma"), get_connection(self._db_path) as conn:
            rows = conn.execute(
                """
                SELECT id, stored_lemma, stored_surface_form, meaning_id, action_type,
                       before_json, after_json, applied_at, reverted_at, provider
                FROM verification_change_log
                WHERE stored_lemma = ?
                ORDER BY applied_at DESC
                LIMIT ?
                """,
                (stored_lemma, limit),
            ).fetchall()
            return [verification_change_log_from_row(row) for row in rows]

    def get_change_log_entry(self, entry_id: int) -> VerificationChangeLogRecord | None:
        with timed_db_operation("wordbank.get_change_log_entry"), get_connection(self._db_path) as conn:
            row = conn.execute(
                """
                SELECT id, stored_lemma, stored_surface_form, meaning_id, action_type,
                       before_json, after_json, applied_at, reverted_at, provider
                FROM verification_change_log
                WHERE id = ?
                LIMIT 1
                """,
                (entry_id,),
            ).fetchone()
            return verification_change_log_from_row(row) if row is not None else None

    def set_change_log_reverted(self, entry_id: int, reverted_at: str) -> None:
        with timed_db_operation("wordbank.set_change_log_reverted"), get_connection(self._db_path) as conn:
            conn.execute(
                """
                UPDATE verification_change_log
                SET reverted_at = ?
                WHERE id = ?
                """,
                (reverted_at, entry_id),
            )
