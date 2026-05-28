from __future__ import annotations

from pathlib import Path

from app.db.repositories.wordbank_models import (
    WordCategoryAssignmentRecord,
    WordCategoryRecord,
    word_category_assignment_from_row,
    word_category_from_row,
)
from app.db.repositories.wordbank_owner_scope import lexeme_scope_exists, meaning_scope_exists
from app.db.sqlite import get_connection, timed_db_operation


class WordbankCategoryMutationRepository:
    _db_path: Path
    _owner_user_id: int

    def ensure_word_category(
        self,
        *,
        label: str,
        normalized_label: str,
    ) -> WordCategoryRecord:
        with timed_db_operation("wordbank.ensure_word_category"), get_connection(self._db_path) as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO wordbank_categories (label, normalized_label)
                VALUES (?, ?)
                """,
                (label, normalized_label),
            )
            row = conn.execute(
                """
                SELECT id, label, normalized_label
                FROM wordbank_categories
                WHERE normalized_label = ?
                LIMIT 1
                """,
                (normalized_label,),
            ).fetchone()
            if row is None:
                raise RuntimeError("Failed to create or load word category.")
            category = word_category_from_row(row)
            if category.label != label:
                conn.execute(
                    """
                    UPDATE wordbank_categories
                    SET label = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (label, category.id),
                )
                row = conn.execute(
                    """
                    SELECT id, label, normalized_label
                    FROM wordbank_categories
                    WHERE id = ?
                    LIMIT 1
                    """,
                    (category.id,),
                ).fetchone()
                if row is None:
                    raise RuntimeError("Failed to reload updated word category.")
            return word_category_from_row(row)

    def replace_word_category_assignments(
        self,
        *,
        lexeme_id: int,
        meaning_id: int | None,
        category_ids: list[int],
    ) -> list[WordCategoryAssignmentRecord]:
        with timed_db_operation("wordbank.replace_word_category_assignments"), get_connection(self._db_path) as conn:
            if not lexeme_scope_exists(conn, lexeme_id, owner_user_id=self._owner_user_id):
                raise LookupError("lexeme was not found")
            if meaning_id is not None and not meaning_scope_exists(
                conn,
                lexeme_id=lexeme_id,
                meaning_id=meaning_id,
                owner_user_id=self._owner_user_id,
            ):
                raise LookupError("meaning was not found")

            if meaning_id is None:
                conn.execute(
                    """
                    DELETE FROM wordbank_category_assignments
                    WHERE lexeme_id = ? AND meaning_id IS NULL
                      AND EXISTS (
                        SELECT 1 FROM lexemes l
                        WHERE l.id = wordbank_category_assignments.lexeme_id
                          AND l.owner_user_id = ?
                      )
                    """,
                    (lexeme_id, self._owner_user_id),
                )
            else:
                conn.execute(
                    """
                    DELETE FROM wordbank_category_assignments
                    WHERE lexeme_id = ? AND meaning_id = ?
                      AND EXISTS (
                        SELECT 1 FROM lexemes l
                        WHERE l.id = wordbank_category_assignments.lexeme_id
                          AND l.owner_user_id = ?
                      )
                    """,
                    (lexeme_id, meaning_id, self._owner_user_id),
                )

            unique_category_ids = list(dict.fromkeys(category_ids))
            for category_id in unique_category_ids:
                conn.execute(
                    """
                    INSERT INTO wordbank_category_assignments (lexeme_id, meaning_id, category_id)
                    VALUES (?, ?, ?)
                    """,
                    (lexeme_id, meaning_id, category_id),
                )

            if not unique_category_ids:
                return []

            if meaning_id is None:
                rows = conn.execute(
                    """
                    SELECT
                        wca.lexeme_id,
                        wca.meaning_id,
                        wc.id AS category_id,
                        wc.label AS category_label,
                        wc.normalized_label AS category_normalized_label
                    FROM wordbank_category_assignments wca
                    JOIN wordbank_categories wc ON wc.id = wca.category_id
                    JOIN lexemes l ON l.id = wca.lexeme_id
                    WHERE wca.lexeme_id = ? AND wca.meaning_id IS NULL
                      AND l.owner_user_id = ?
                    ORDER BY wc.normalized_label ASC
                    """,
                    (lexeme_id, self._owner_user_id),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT
                        wca.lexeme_id,
                        wca.meaning_id,
                        wc.id AS category_id,
                        wc.label AS category_label,
                        wc.normalized_label AS category_normalized_label
                    FROM wordbank_category_assignments wca
                    JOIN wordbank_categories wc ON wc.id = wca.category_id
                    JOIN lexemes l ON l.id = wca.lexeme_id
                    WHERE wca.lexeme_id = ? AND wca.meaning_id = ?
                      AND l.owner_user_id = ?
                    ORDER BY wc.normalized_label ASC
                    """,
                    (lexeme_id, meaning_id, self._owner_user_id),
                ).fetchall()
        return [word_category_assignment_from_row(row) for row in rows]
