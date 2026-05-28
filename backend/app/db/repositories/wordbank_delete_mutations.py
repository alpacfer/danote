from __future__ import annotations

from pathlib import Path

from app.db.repositories.wordbank_owner_scope import lexeme_scope_exists
from app.db.sqlite import get_connection, timed_db_operation


class WordbankDeleteRepository:
    _db_path: Path
    _owner_user_id: int

    def delete_verification_record(
        self,
        *,
        lexeme_id: int,
        meaning_id: int | None,
        stored_surface_form: str | None,
    ) -> None:
        with timed_db_operation("wordbank.delete_verification_record"), get_connection(self._db_path) as conn:
            if not lexeme_scope_exists(conn, lexeme_id, owner_user_id=self._owner_user_id):
                raise LookupError("lexeme was not found")
            if meaning_id is None and stored_surface_form is None:
                conn.execute(
                    """
                    DELETE FROM wordbank_verification_records
                    WHERE lexeme_id = ? AND meaning_id IS NULL AND stored_surface_form IS NULL
                      AND EXISTS (
                        SELECT 1 FROM lexemes l
                        WHERE l.id = wordbank_verification_records.lexeme_id
                          AND l.owner_user_id = ?
                      )
                    """,
                    (lexeme_id, self._owner_user_id),
                )
            elif meaning_id is None:
                conn.execute(
                    """
                    DELETE FROM wordbank_verification_records
                    WHERE lexeme_id = ? AND meaning_id IS NULL AND stored_surface_form = ?
                      AND EXISTS (
                        SELECT 1 FROM lexemes l
                        WHERE l.id = wordbank_verification_records.lexeme_id
                          AND l.owner_user_id = ?
                      )
                    """,
                    (lexeme_id, stored_surface_form, self._owner_user_id),
                )
            elif stored_surface_form is None:
                conn.execute(
                    """
                    DELETE FROM wordbank_verification_records
                    WHERE lexeme_id = ? AND meaning_id = ? AND stored_surface_form IS NULL
                      AND EXISTS (
                        SELECT 1 FROM lexemes l
                        WHERE l.id = wordbank_verification_records.lexeme_id
                          AND l.owner_user_id = ?
                      )
                    """,
                    (lexeme_id, meaning_id, self._owner_user_id),
                )
            else:
                conn.execute(
                    """
                    DELETE FROM wordbank_verification_records
                    WHERE lexeme_id = ? AND meaning_id = ? AND stored_surface_form = ?
                      AND EXISTS (
                        SELECT 1 FROM lexemes l
                        WHERE l.id = wordbank_verification_records.lexeme_id
                          AND l.owner_user_id = ?
                      )
                    """,
                    (lexeme_id, meaning_id, stored_surface_form, self._owner_user_id),
                )

    def delete_lexeme_meaning(self, meaning_id: int) -> bool:
        """Delete a meaning and unsave sentence tokens before SQLite can cascade-delete them."""
        with timed_db_operation("wordbank.delete_lexeme_meaning"), get_connection(self._db_path) as conn:
            row = conn.execute(
                """SELECT lm.lexeme_id
                FROM lexeme_meanings lm
                JOIN lexemes l ON l.id = lm.lexeme_id
                WHERE lm.id = ? AND l.owner_user_id = ?
                LIMIT 1""",
                (meaning_id, self._owner_user_id),
            ).fetchone()
            if row is None:
                raise LookupError("meaning was not found")

            lexeme_id = int(row["lexeme_id"])

            count_row = conn.execute(
                "SELECT COUNT(*) as cnt FROM lexeme_meanings WHERE lexeme_id = ?",
                (lexeme_id,),
            ).fetchone()
            meaning_count = int(count_row["cnt"]) if count_row else 0

            if meaning_count > 1:
                self._unsave_tokens_for_meaning(conn, meaning_id)
                conn.execute(
                    "DELETE FROM surface_forms WHERE meaning_id = ?",
                    (meaning_id,),
                )
                conn.execute(
                    "DELETE FROM lexeme_meanings WHERE id = ?",
                    (meaning_id,),
                )
                return False

            self._unsave_tokens_for_lexeme(conn, lexeme_id)
            conn.execute(
                "DELETE FROM lexemes WHERE id = ?",
                (lexeme_id,),
            )
            return True

    def delete_lexeme(self, lexeme_id: int) -> None:
        """Delete a lexeme and unsave sentence tokens before SQLite can cascade-delete them."""
        with timed_db_operation("wordbank.delete_lexeme"), get_connection(self._db_path) as conn:
            row = conn.execute(
                "SELECT id FROM lexemes WHERE id = ? AND owner_user_id = ? LIMIT 1",
                (lexeme_id, self._owner_user_id),
            ).fetchone()
            if row is None:
                raise LookupError("lexeme was not found")

            self._unsave_tokens_for_lexeme(conn, lexeme_id)
            conn.execute(
                "DELETE FROM lexemes WHERE id = ?",
                (lexeme_id,),
            )

    def delete_lexeme_by_lemma(self, lemma: str) -> None:
        """Delete a lexeme by lemma and unsave sentence tokens before SQLite can cascade-delete them."""
        with timed_db_operation("wordbank.delete_lexeme_by_lemma"), get_connection(self._db_path) as conn:
            row = conn.execute(
                "SELECT id FROM lexemes WHERE lemma = ? AND owner_user_id = ? LIMIT 1",
                (lemma, self._owner_user_id),
            ).fetchone()
            if row is None:
                raise LookupError("lemma was not found")

            lexeme_id = int(row["id"])

            self._unsave_tokens_for_lexeme(conn, lexeme_id)
            conn.execute(
                "DELETE FROM lexemes WHERE id = ?",
                (lexeme_id,),
            )

    def _unsave_tokens_for_meaning(self, conn, meaning_id: int) -> None:
        conn.execute(
            """
            UPDATE sentence_bank_tokens
            SET save_status = 'unsaved',
                lexeme_id = NULL,
                meaning_id = NULL,
                stored_lemma = NULL,
                cor_id = NULL
            WHERE meaning_id = ?
              AND EXISTS (
                SELECT 1
                FROM sentence_bank sb
                WHERE sb.id = sentence_bank_tokens.sentence_id
                  AND sb.owner_user_id = ?
              )
            """,
            (meaning_id, self._owner_user_id),
        )

    def _unsave_tokens_for_lexeme(self, conn, lexeme_id: int) -> None:
        conn.execute(
            """
            UPDATE sentence_bank_tokens
            SET save_status = 'unsaved',
                lexeme_id = NULL,
                meaning_id = NULL,
                stored_lemma = NULL,
                cor_id = NULL
            WHERE lexeme_id = ?
              AND EXISTS (
                SELECT 1
                FROM sentence_bank sb
                WHERE sb.id = sentence_bank_tokens.sentence_id
                  AND sb.owner_user_id = ?
              )
            """,
            (lexeme_id, self._owner_user_id),
        )
