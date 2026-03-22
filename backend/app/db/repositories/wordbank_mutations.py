from __future__ import annotations

import json
from pathlib import Path

from app.db.repositories.wordbank_models import (
    LexemeMeaningRecord,
    RelatedWordWriteRecord,
    SurfaceFormRecord,
    VerificationRecord,
    lexeme_meaning_from_row,
    surface_form_from_row,
    verification_record_from_row,
)
from app.db.sqlite import get_connection, timed_db_operation


class WordbankMutationRepository:
    _db_path: Path

    def replace_lexeme_translation(
        self,
        *,
        lexeme_id: int,
        english_translation: str | None,
        provider: str | None,
    ) -> None:
        with timed_db_operation("wordbank.replace_lexeme_translation"), get_connection(self._db_path) as conn:
            conn.execute(
                """
                UPDATE lexemes
                SET english_translation = ?,
                    translation_provider = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (english_translation, provider if english_translation else None, lexeme_id),
            )

    def replace_lexeme_meaning_translation(
        self,
        *,
        meaning_id: int,
        english_translation: str | None,
    ) -> None:
        with timed_db_operation("wordbank.replace_lexeme_meaning_translation"), get_connection(self._db_path) as conn:
            conn.execute(
                """
                UPDATE lexeme_meanings
                SET english_translation = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (english_translation, meaning_id),
            )

    def insert_additional_translation(
        self,
        *,
        lexeme_id: int,
        meaning_id: int | None,
        english_translation: str,
        source: str = "related_words",
    ) -> bool:
        with timed_db_operation("wordbank.insert_additional_translation"), get_connection(self._db_path) as conn:
            if meaning_id is None:
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO wordbank_additional_translations (
                        lexeme_id,
                        meaning_id,
                        english_translation,
                        source
                    )
                    VALUES (?, NULL, ?, ?)
                    """,
                    (lexeme_id, english_translation, source),
                )
            else:
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO wordbank_additional_translations (
                        lexeme_id,
                        meaning_id,
                        english_translation,
                        source
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (lexeme_id, meaning_id, english_translation, source),
                )
        return cursor.rowcount == 1

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

    def replace_lexeme_metadata(self, *, lexeme_id: int, pos_tag: str | None, morphology: str | None) -> None:
        with timed_db_operation("wordbank.replace_lexeme_metadata"), get_connection(self._db_path) as conn:
            conn.execute(
                """
                UPDATE lexemes
                SET pos_tag = ?,
                    morphology = ?
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

    def replace_lexeme_meaning_metadata(
        self,
        *,
        meaning_id: int,
        pos_tag: str | None,
        morphology: str | None,
    ) -> None:
        with timed_db_operation("wordbank.replace_lexeme_meaning_metadata"), get_connection(self._db_path) as conn:
            conn.execute(
                """
                UPDATE lexeme_meanings
                SET pos_tag = ?,
                    morphology = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (pos_tag, morphology, meaning_id),
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

    def replace_related_words(
        self,
        *,
        owner_lexeme_id: int,
        items: list[RelatedWordWriteRecord],
    ) -> None:
        with timed_db_operation("wordbank.replace_related_words"), get_connection(self._db_path) as conn:
            conn.execute(
                """
                DELETE FROM wordbank_related_words
                WHERE owner_lexeme_id = ?
                """,
                (owner_lexeme_id,),
            )
            for item in items:
                conn.execute(
                    """
                    INSERT INTO wordbank_related_words (
                        owner_lexeme_id,
                        relation_type,
                        sort_order,
                        related_lemma,
                        english_translation,
                        pos_tag
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        owner_lexeme_id,
                        item.relation_type,
                        item.sort_order,
                        item.related_lemma,
                        item.english_translation,
                        item.pos_tag,
                    ),
                )

    def delete_verification_record(
        self,
        *,
        lexeme_id: int,
        meaning_id: int | None,
        stored_surface_form: str | None,
    ) -> None:
        with timed_db_operation("wordbank.delete_verification_record"), get_connection(self._db_path) as conn:
            if meaning_id is None and stored_surface_form is None:
                conn.execute(
                    """
                    DELETE FROM wordbank_verification_records
                    WHERE lexeme_id = ? AND meaning_id IS NULL AND stored_surface_form IS NULL
                    """,
                    (lexeme_id,),
                )
            elif meaning_id is None:
                conn.execute(
                    """
                    DELETE FROM wordbank_verification_records
                    WHERE lexeme_id = ? AND meaning_id IS NULL AND stored_surface_form = ?
                    """,
                    (lexeme_id, stored_surface_form),
                )
            elif stored_surface_form is None:
                conn.execute(
                    """
                    DELETE FROM wordbank_verification_records
                    WHERE lexeme_id = ? AND meaning_id = ? AND stored_surface_form IS NULL
                    """,
                    (lexeme_id, meaning_id),
                )
            else:
                conn.execute(
                    """
                    DELETE FROM wordbank_verification_records
                    WHERE lexeme_id = ? AND meaning_id = ? AND stored_surface_form = ?
                    """,
                    (lexeme_id, meaning_id, stored_surface_form),
                )


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
