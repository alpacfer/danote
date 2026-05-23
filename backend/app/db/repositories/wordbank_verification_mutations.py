from __future__ import annotations

import json
from pathlib import Path

from app.db.repositories.wordbank_models import (
    VerificationRecord,
    verification_record_from_row,
)
from app.db.sqlite import get_connection, timed_db_operation


class WordbankVerificationRepository:
    _db_path: Path
    _owner_user_id: int

    def upsert_verification_record(
        self,
        *,
        lexeme_id: int,
        meaning_id: int | None,
        status: str,
        provider: str | None,
        reviewer_role: str | None,
        stored_surface_form: str | None,
        message: str,
        problem: str | None,
        change_to_implement: str | None,
        suggested_actions: list[dict[str, object]],
        requested_at: str,
        completed_at: str | None,
        review_intent: str = "general",
        latest_snapshot_hash: str | None = None,
        request_generation: int = 0,
    ) -> VerificationRecord:
        with timed_db_operation("wordbank.upsert_verification_record"), get_connection(self._db_path) as conn:
            if meaning_id is None and stored_surface_form is None:
                existing_row = conn.execute(
                    """
                    SELECT id
                    FROM wordbank_verification_records
                    WHERE lexeme_id = ? AND meaning_id IS NULL AND stored_surface_form IS NULL
                    LIMIT 1
                    """,
                    (lexeme_id,),
                ).fetchone()
            elif meaning_id is None:
                existing_row = conn.execute(
                    """
                    SELECT id
                    FROM wordbank_verification_records
                    WHERE lexeme_id = ? AND meaning_id IS NULL AND stored_surface_form = ?
                    LIMIT 1
                    """,
                    (lexeme_id, stored_surface_form),
                ).fetchone()
            elif stored_surface_form is None:
                existing_row = conn.execute(
                    """
                    SELECT id
                    FROM wordbank_verification_records
                    WHERE lexeme_id = ? AND meaning_id = ? AND stored_surface_form IS NULL
                    LIMIT 1
                    """,
                    (lexeme_id, meaning_id),
                ).fetchone()
            else:
                existing_row = conn.execute(
                    """
                    SELECT id
                    FROM wordbank_verification_records
                    WHERE lexeme_id = ? AND meaning_id = ? AND stored_surface_form = ?
                    LIMIT 1
                    """,
                    (lexeme_id, meaning_id, stored_surface_form),
                ).fetchone()

            actions_json = json.dumps(suggested_actions, ensure_ascii=True, sort_keys=True)
            if existing_row is None:
                cursor = conn.execute(
                    """
                    INSERT INTO wordbank_verification_records (
                        lexeme_id,
                        meaning_id,
                        status,
                        provider,
                        reviewer_role,
                        stored_surface_form,
                        message,
                        problem,
                        change_to_implement,
                        suggested_actions_json,
                        requested_at,
                        completed_at,
                        review_intent,
                        latest_snapshot_hash,
                        request_generation
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        lexeme_id,
                        meaning_id,
                        status,
                        provider,
                        reviewer_role,
                        stored_surface_form,
                        message,
                        problem,
                        change_to_implement,
                        actions_json,
                        requested_at,
                        completed_at,
                        review_intent,
                        latest_snapshot_hash,
                        request_generation,
                    ),
                )
                if cursor.lastrowid is None:
                    raise ValueError("Failed to create verification record.")
                record_id = int(cursor.lastrowid)
            else:
                record_id = int(existing_row["id"])
                conn.execute(
                    """
                    UPDATE wordbank_verification_records
                    SET status = ?,
                        provider = ?,
                        reviewer_role = ?,
                        stored_surface_form = ?,
                        message = ?,
                        problem = ?,
                        change_to_implement = ?,
                        suggested_actions_json = ?,
                        requested_at = ?,
                        completed_at = ?,
                        review_intent = ?,
                        latest_snapshot_hash = ?,
                        request_generation = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (
                        status,
                        provider,
                        reviewer_role,
                        stored_surface_form,
                        message,
                        problem,
                        change_to_implement,
                        actions_json,
                        requested_at,
                        completed_at,
                        review_intent,
                        latest_snapshot_hash,
                        request_generation,
                        record_id,
                    ),
                )

            row = conn.execute(
                """
                SELECT
                    id,
                    lexeme_id,
                    meaning_id,
                    status,
                    provider,
                    reviewer_role,
                    stored_surface_form,
                    message,
                    problem,
                    change_to_implement,
                    suggested_actions_json,
                    requested_at,
                    completed_at,
                    review_intent,
                    latest_snapshot_hash,
                    request_generation
                FROM wordbank_verification_records
                WHERE id = ?
                LIMIT 1
                """,
                (record_id,),
            ).fetchone()
        if row is None:
            raise RuntimeError("Failed to upsert verification record")
        return verification_record_from_row(row)
