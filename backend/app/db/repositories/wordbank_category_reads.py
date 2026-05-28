from __future__ import annotations

from pathlib import Path

from app.db.repositories.wordbank_models import (
    WordCategoryAssignmentRecord,
    WordCategoryRecord,
    word_category_assignment_from_row,
    word_category_from_row,
)
from app.db.sqlite import get_connection, timed_db_operation


class WordbankCategoryReadRepository:
    _db_path: Path
    _owner_user_id: int

    def list_word_categories(self) -> list[WordCategoryRecord]:
        with timed_db_operation("wordbank.list_word_categories"), get_connection(
            self._db_path, read_only=True
        ) as conn:
            rows = conn.execute(
                """
                SELECT id, label, normalized_label
                FROM wordbank_categories
                ORDER BY normalized_label ASC
                """
            ).fetchall()
        return [word_category_from_row(row) for row in rows]

    def list_word_category_assignments(self, lexeme_id: int) -> list[WordCategoryAssignmentRecord]:
        with timed_db_operation("wordbank.list_word_category_assignments"), get_connection(
            self._db_path, read_only=True
        ) as conn:
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
                WHERE wca.lexeme_id = ? AND l.owner_user_id = ?
                ORDER BY wca.meaning_id IS NULL DESC, wca.meaning_id ASC, wc.normalized_label ASC
                """,
                (lexeme_id, self._owner_user_id),
            ).fetchall()
        return [word_category_assignment_from_row(row) for row in rows]
