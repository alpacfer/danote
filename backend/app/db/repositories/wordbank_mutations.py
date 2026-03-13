from __future__ import annotations

from pathlib import Path

from app.db.repositories.wordbank_models import (
    LexemeMeaningRecord,
    SurfaceFormRecord,
    lexeme_meaning_from_row,
    surface_form_from_row,
)
from app.db.sqlite import get_connection, timed_db_operation


class WordbankMutationRepository:
    _db_path: Path

    def update_lexeme_metadata(self, *, lexeme_id: int, pos_tag: str | None, morphology: str | None) -> None:
        with timed_db_operation("wordbank.update_lexeme_metadata"), get_connection(self._db_path) as conn:
            conn.execute(
                """
                UPDATE lexemes
                SET pos_tag = COALESCE(pos_tag, ?),
                    morphology = COALESCE(morphology, ?)
                WHERE id = ?
                """,
                (pos_tag, morphology, lexeme_id),
            )

    def update_surface_form_metadata(
        self,
        *,
        surface_form_id: int,
        pos_tag: str | None,
        morphology: str | None,
    ) -> None:
        with timed_db_operation("wordbank.update_surface_form_metadata"), get_connection(self._db_path) as conn:
            conn.execute(
                """
                UPDATE surface_forms
                SET pos_tag = COALESCE(pos_tag, ?),
                    morphology = COALESCE(morphology, ?)
                WHERE id = ?
                """,
                (pos_tag, morphology, surface_form_id),
            )

    def insert_or_load_lexeme(
        self,
        *,
        stored_lemma: str,
        translation: str | None,
        provider: str | None,
        pos_tag: str | None,
        morphology: str | None,
        source: str = "manual",
    ) -> tuple[int, bool]:
        with timed_db_operation("wordbank.insert_or_load_lexeme"), get_connection(self._db_path) as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO lexemes (
                    lemma,
                    source,
                    english_translation,
                    translation_provider,
                    pos_tag,
                    morphology
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    stored_lemma,
                    source,
                    translation,
                    provider if translation else None,
                    pos_tag,
                    morphology,
                ),
            )
            lexeme_row = conn.execute(
                "SELECT id FROM lexemes WHERE lemma = ? LIMIT 1",
                (stored_lemma,),
            ).fetchone()
            if lexeme_row is None:
                raise RuntimeError("Failed to create or load lexeme")
            lexeme_id = int(lexeme_row["id"])
            if translation:
                conn.execute(
                    """
                    UPDATE lexemes
                    SET english_translation = COALESCE(english_translation, ?),
                        translation_provider = COALESCE(translation_provider, ?)
                    WHERE id = ?
                    """,
                    (translation, provider, lexeme_id),
                )
            conn.execute(
                """
                UPDATE lexemes
                SET pos_tag = COALESCE(pos_tag, ?),
                    morphology = COALESCE(morphology, ?)
                WHERE id = ?
                """,
                (pos_tag, morphology, lexeme_id),
            )
        return lexeme_id, cursor.rowcount == 1


    def insert_or_update_surface_form(
        self,
        *,
        lexeme_id: int,
        meaning_id: int | None,
        form: str,
        pos_tag: str | None,
        morphology: str | None,
        source: str = "manual",
    ) -> tuple[SurfaceFormRecord, bool]:
        with timed_db_operation("wordbank.insert_or_update_surface_form"), get_connection(self._db_path) as conn:
            row = _select_surface_form_row(conn, lexeme_id=lexeme_id, meaning_id=meaning_id, form=form)
            inserted = False
            if row is None:
                cursor = conn.execute(
                    """
                    INSERT INTO surface_forms (
                        lexeme_id,
                        meaning_id,
                        form,
                        source,
                        pos_tag,
                        morphology,
                        seen_count,
                        last_seen_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (
                        lexeme_id,
                        meaning_id,
                        form,
                        source,
                        pos_tag,
                        morphology,
                        1,
                    ),
                )
                row = conn.execute(
                    """
                    SELECT
                        id,
                        lexeme_id,
                        form,
                        source,
                        pos_tag,
                        morphology,
                        (
                            SELECT sfcv.cor_id
                            FROM surface_form_cor_variants sfcv
                            WHERE sfcv.surface_form_id = surface_forms.id
                            ORDER BY sfcv.id ASC
                            LIMIT 1
                        ) AS cor_id,
                        meaning_id,
                        CASE WHEN pronunciation_audio IS NOT NULL THEN 1 ELSE 0 END AS has_pronunciation
                    FROM surface_forms
                    WHERE id = ?
                    LIMIT 1
                    """,
                    (cursor.lastrowid,),
                ).fetchone()
                inserted = True
            else:
                conn.execute(
                    """
                    UPDATE surface_forms
                    SET seen_count = seen_count + 1,
                        last_seen_at = CURRENT_TIMESTAMP,
                        pos_tag = COALESCE(pos_tag, ?),
                        morphology = COALESCE(morphology, ?)
                    WHERE id = ?
                    """,
                    (pos_tag, morphology, int(row["id"])),
                )
                row = conn.execute(
                    """
                    SELECT
                        id,
                        lexeme_id,
                        form,
                        source,
                        pos_tag,
                        morphology,
                        (
                            SELECT sfcv.cor_id
                            FROM surface_form_cor_variants sfcv
                            WHERE sfcv.surface_form_id = surface_forms.id
                            ORDER BY sfcv.id ASC
                            LIMIT 1
                        ) AS cor_id,
                        meaning_id,
                        CASE WHEN pronunciation_audio IS NOT NULL THEN 1 ELSE 0 END AS has_pronunciation
                    FROM surface_forms
                    WHERE id = ?
                    LIMIT 1
                    """,
                    (int(row["id"]),),
                ).fetchone()
        if row is None:
            raise RuntimeError("Failed to create or load surface form")
        return surface_form_from_row(row), inserted


    def insert_surface_form_cor_variant(self, *, surface_form_id: int, cor_id: str) -> bool:
        with timed_db_operation("wordbank.insert_surface_form_cor_variant"), get_connection(self._db_path) as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO surface_form_cor_variants (
                    surface_form_id,
                    cor_id
                )
                VALUES (?, ?)
                """,
                (surface_form_id, cor_id),
            )
        return cursor.rowcount == 1


    def upsert_lexeme_meaning(
        self,
        *,
        lexeme_id: int,
        meaning_key: str,
        cor_lemma_idx: int | None,
        gloss: str | None,
        english_translation: str | None,
        pos_tag: str | None,
        morphology: str | None,
        ) -> tuple[LexemeMeaningRecord, bool]:
        with timed_db_operation("wordbank.upsert_lexeme_meaning"), get_connection(self._db_path) as conn:
            row = None
            if cor_lemma_idx is not None:
                row = conn.execute(
                    """
                    SELECT
                        id,
                        meaning_key,
                        cor_lemma_idx,
                        gloss,
                        english_translation,
                        pos_tag,
                        morphology
                    FROM lexeme_meanings
                    WHERE lexeme_id = ? AND cor_lemma_idx = ?
                    LIMIT 1
                    """,
                    (lexeme_id, cor_lemma_idx),
                ).fetchone()
            if row is None and cor_lemma_idx is None:
                row = conn.execute(
                    """
                    SELECT
                        id,
                        meaning_key,
                        cor_lemma_idx,
                        gloss,
                        english_translation,
                        pos_tag,
                        morphology
                    FROM lexeme_meanings
                    WHERE lexeme_id = ? AND meaning_key = ?
                    LIMIT 1
                    """,
                    (lexeme_id, meaning_key),
                ).fetchone()

            inserted = False
            if row is None:
                cursor = conn.execute(
                    """
                    INSERT INTO lexeme_meanings (
                        lexeme_id,
                        meaning_key,
                        cor_lemma_idx,
                        gloss,
                        english_translation,
                        pos_tag,
                        morphology
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        lexeme_id,
                        meaning_key,
                        cor_lemma_idx,
                        gloss,
                        english_translation,
                        pos_tag,
                        morphology,
                    ),
                )
                row = conn.execute(
                    """
                    SELECT
                        id,
                        meaning_key,
                        cor_lemma_idx,
                        gloss,
                        english_translation,
                        pos_tag,
                        morphology
                    FROM lexeme_meanings
                    WHERE id = ?
                    LIMIT 1
                    """,
                    (cursor.lastrowid,),
                ).fetchone()
                inserted = True
            else:
                conn.execute(
                    """
                    UPDATE lexeme_meanings
                    SET meaning_key = COALESCE(?, meaning_key),
                        cor_lemma_idx = COALESCE(cor_lemma_idx, ?),
                        gloss = COALESCE(gloss, ?),
                        english_translation = COALESCE(english_translation, ?),
                        pos_tag = COALESCE(pos_tag, ?),
                        morphology = COALESCE(morphology, ?),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (
                        meaning_key,
                        cor_lemma_idx,
                        gloss,
                        english_translation,
                        pos_tag,
                        morphology,
                        int(row["id"]),
                    ),
                )
                row = conn.execute(
                    """
                    SELECT
                        id,
                        meaning_key,
                        cor_lemma_idx,
                        gloss,
                        english_translation,
                        pos_tag,
                        morphology
                    FROM lexeme_meanings
                    WHERE id = ?
                    LIMIT 1
                    """,
                    (int(row["id"]),),
                ).fetchone()
        if row is None:
            raise RuntimeError("Failed to create or load lexeme meaning")
        return lexeme_meaning_from_row(row), inserted


def _select_surface_form_row(conn, *, lexeme_id: int, meaning_id: int | None, form: str):
    if meaning_id is None:
        return conn.execute(
            """
            SELECT
                id,
                lexeme_id,
                form,
                source,
                pos_tag,
                morphology,
                (
                    SELECT sfcv.cor_id
                    FROM surface_form_cor_variants sfcv
                    WHERE sfcv.surface_form_id = surface_forms.id
                    ORDER BY sfcv.id ASC
                    LIMIT 1
                ) AS cor_id,
                meaning_id,
                CASE WHEN pronunciation_audio IS NOT NULL THEN 1 ELSE 0 END AS has_pronunciation
            FROM surface_forms
            WHERE lexeme_id = ? AND meaning_id IS NULL AND form = ?
            LIMIT 1
            """,
            (lexeme_id, form),
        ).fetchone()
    return conn.execute(
        """
        SELECT
            id,
            lexeme_id,
            form,
            source,
            pos_tag,
            morphology,
            (
                SELECT sfcv.cor_id
                FROM surface_form_cor_variants sfcv
                WHERE sfcv.surface_form_id = surface_forms.id
                ORDER BY sfcv.id ASC
                LIMIT 1
            ) AS cor_id,
            meaning_id,
            CASE WHEN pronunciation_audio IS NOT NULL THEN 1 ELSE 0 END AS has_pronunciation
        FROM surface_forms
        WHERE meaning_id = ? AND form = ?
        LIMIT 1
        """,
        (meaning_id, form),
    ).fetchone()
