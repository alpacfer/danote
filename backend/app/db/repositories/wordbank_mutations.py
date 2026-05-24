from __future__ import annotations

from pathlib import Path

from app.db.repositories.wordbank_models import (
    LexemeMeaningRecord,
    RelatedWordWriteRecord,
    SurfaceFormRecord,
    lexeme_meaning_from_row,
    surface_form_from_row,
)
from app.db.repositories.wordbank_surface_form_queries import select_surface_form_row
from app.db.sqlite import get_connection, timed_db_operation


class WordbankMutationRepository:
    _db_path: Path
    _owner_user_id: int

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
                WHERE id = ? AND owner_user_id = ?
                """,
                (english_translation, provider if english_translation else None, lexeme_id, self._owner_user_id),
            )
            # Propagate to denormalized sentence_bank_tokens.english_translation so
            # every saved sentence containing this lemma (with no meaning scope) reflects
            # the new translation immediately.
            conn.execute(
                """
                UPDATE sentence_bank_tokens
                SET english_translation = ?
                WHERE lexeme_id = ?
                  AND meaning_id IS NULL
                  AND save_status = 'saved'
                  AND EXISTS (
                    SELECT 1
                    FROM sentence_bank sb
                    WHERE sb.id = sentence_bank_tokens.sentence_id
                      AND sb.owner_user_id = ?
                  )
                """,
                (english_translation, lexeme_id, self._owner_user_id),
            )

    def replace_lexeme_source(self, *, lexeme_id: int, source: str) -> None:
        with timed_db_operation("wordbank.replace_lexeme_source"), get_connection(self._db_path) as conn:
            conn.execute(
                """
                UPDATE lexemes
                SET source = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND owner_user_id = ?
                """,
                (source, lexeme_id, self._owner_user_id),
            )

    def overwrite_lexeme_meaning_descriptor(
        self,
        *,
        meaning_id: int,
        meaning_key: str,
        gloss: str | None,
        english_translation: str | None,
    ) -> None:
        """Overwrite (NOT COALESCE) the meaning_key / gloss / english_translation
        for a meaning row. Used by the MWE dedupe path in
        ``add_word_from_search_seed`` to replace the sentence-auto-created
        meaning's tentative descriptor with the user's first explicit save.
        Other fields are left untouched.
        """
        with timed_db_operation("wordbank.overwrite_lexeme_meaning_descriptor"), get_connection(self._db_path) as conn:
            conn.execute(
                """
                UPDATE lexeme_meanings
                SET meaning_key = ?,
                    gloss = ?,
                    english_translation = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                  AND EXISTS (
                    SELECT 1 FROM lexemes l
                    WHERE l.id = lexeme_meanings.lexeme_id
                      AND l.owner_user_id = ?
                  )
                """,
                (meaning_key, gloss, english_translation, meaning_id, self._owner_user_id),
            )
            # Propagate to denormalized sentence_bank_tokens.english_translation so
            # every saved sentence whose token references this meaning reflects
            # the user's chosen English translation immediately.
            conn.execute(
                """
                UPDATE sentence_bank_tokens
                SET english_translation = ?
                WHERE meaning_id = ?
                  AND save_status = 'saved'
                  AND EXISTS (
                    SELECT 1
                    FROM sentence_bank sb
                    WHERE sb.id = sentence_bank_tokens.sentence_id
                      AND sb.owner_user_id = ?
                  )
                """,
                (english_translation, meaning_id, self._owner_user_id),
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
                  AND EXISTS (
                    SELECT 1 FROM lexemes l
                    WHERE l.id = lexeme_meanings.lexeme_id
                      AND l.owner_user_id = ?
                  )
                """,
                (english_translation, meaning_id, self._owner_user_id),
            )
            # Propagate to denormalized sentence_bank_tokens.english_translation so
            # every saved sentence whose token references this meaning reflects the new
            # translation immediately (sentence page + sentence search dialog).
            conn.execute(
                """
                UPDATE sentence_bank_tokens
                SET english_translation = ?
                WHERE meaning_id = ?
                  AND save_status = 'saved'
                  AND EXISTS (
                    SELECT 1
                    FROM sentence_bank sb
                    WHERE sb.id = sentence_bank_tokens.sentence_id
                      AND sb.owner_user_id = ?
                  )
                """,
                (english_translation, meaning_id, self._owner_user_id),
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
                WHERE id = ? AND owner_user_id = ?
                """,
                (pos_tag, morphology, lexeme_id, self._owner_user_id),
            )

    def replace_lexeme_metadata(self, *, lexeme_id: int, pos_tag: str | None, morphology: str | None) -> None:
        with timed_db_operation("wordbank.replace_lexeme_metadata"), get_connection(self._db_path) as conn:
            conn.execute(
                """
                UPDATE lexemes
                SET pos_tag = ?,
                    morphology = ?
                WHERE id = ? AND owner_user_id = ?
                """,
                (pos_tag, morphology, lexeme_id, self._owner_user_id),
            )

    def assign_orphan_surface_forms_to_meaning(
        self,
        *,
        lexeme_id: int,
        meaning_id: int,
    ) -> int:
        with timed_db_operation("wordbank.assign_orphan_surface_forms_to_meaning"), get_connection(self._db_path) as conn:
            cursor = conn.execute(
                """
                UPDATE surface_forms
                SET meaning_id = ?
                WHERE lexeme_id = ?
                  AND meaning_id IS NULL
                  AND EXISTS (
                    SELECT 1 FROM lexemes l
                    WHERE l.id = surface_forms.lexeme_id
                      AND l.owner_user_id = ?
                  )
                """,
                (meaning_id, lexeme_id, self._owner_user_id),
            )
            return cursor.rowcount

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
                  AND EXISTS (
                    SELECT 1
                    FROM lexemes l
                    JOIN surface_forms sf ON sf.lexeme_id = l.id
                    WHERE sf.id = surface_forms.id
                      AND l.owner_user_id = ?
                  )
                """,
                (pos_tag, morphology, surface_form_id, self._owner_user_id),
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
                  AND EXISTS (
                    SELECT 1 FROM lexemes l
                    WHERE l.id = lexeme_meanings.lexeme_id
                      AND l.owner_user_id = ?
                  )
                """,
                (pos_tag, morphology, meaning_id, self._owner_user_id),
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
        dictionary_status: str = "unknown",
    ) -> tuple[int, bool]:
        with timed_db_operation("wordbank.insert_or_load_lexeme"), get_connection(self._db_path) as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO lexemes (
                    owner_user_id,
                    lemma,
                    source,
                    dictionary_status,
                    english_translation,
                    translation_provider,
                    pos_tag,
                    morphology
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self._owner_user_id,
                    stored_lemma,
                    source,
                    dictionary_status,
                    translation,
                    provider if translation else None,
                    pos_tag,
                    morphology,
                ),
            )
            lexeme_row = conn.execute(
                "SELECT id FROM lexemes WHERE owner_user_id = ? AND lemma = ? LIMIT 1",
                (self._owner_user_id, stored_lemma),
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
                    WHERE id = ? AND owner_user_id = ?
                    """,
                    (translation, provider, lexeme_id, self._owner_user_id),
                )
            conn.execute(
                """
                UPDATE lexemes
                SET pos_tag = COALESCE(pos_tag, ?),
                    morphology = COALESCE(morphology, ?),
                    dictionary_status = CASE
                        WHEN dictionary_status = 'cor' OR ? = 'cor' THEN 'cor'
                        WHEN dictionary_status = 'generated_non_cor' OR ? = 'generated_non_cor' THEN 'generated_non_cor'
                        ELSE 'unknown'
                    END
                WHERE id = ? AND owner_user_id = ?
                """,
                (pos_tag, morphology, dictionary_status, dictionary_status, lexeme_id, self._owner_user_id),
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
            row = select_surface_form_row(conn, lexeme_id=lexeme_id, meaning_id=meaning_id, form=form)
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
        dictionary_status: str = "unknown",
        gloss: str | None,
        english_translation: str | None,
        pos_tag: str | None,
        morphology: str | None,
        ) -> tuple[LexemeMeaningRecord, bool]:
        with timed_db_operation("wordbank.upsert_lexeme_meaning"), get_connection(self._db_path) as conn:
            if conn.execute(
                "SELECT 1 FROM lexemes WHERE id = ? AND owner_user_id = ? LIMIT 1",
                (lexeme_id, self._owner_user_id),
            ).fetchone() is None:
                raise LookupError("lexeme was not found")
            row = None
            if cor_lemma_idx is not None:
                row = conn.execute(
                    """
                    SELECT
                        id,
                        meaning_key,
                        cor_lemma_idx,
                        dictionary_status,
                        gloss,
                        english_translation,
                        pos_tag,
                        morphology,
                        lexeme_id
                    FROM lexeme_meanings
                    WHERE lexeme_id = ? AND cor_lemma_idx = ?
                      AND EXISTS (
                        SELECT 1 FROM lexemes l
                        WHERE l.id = lexeme_meanings.lexeme_id
                          AND l.owner_user_id = ?
                      )
                    LIMIT 1
                    """,
                    (lexeme_id, cor_lemma_idx, self._owner_user_id),
                ).fetchone()
            if row is None and cor_lemma_idx is None:
                row = conn.execute(
                    """
                    SELECT
                        id,
                        meaning_key,
                        cor_lemma_idx,
                        dictionary_status,
                        gloss,
                        english_translation,
                        pos_tag,
                        morphology,
                        lexeme_id
                    FROM lexeme_meanings
                    WHERE lexeme_id = ? AND meaning_key = ?
                      AND EXISTS (
                        SELECT 1 FROM lexemes l
                        WHERE l.id = lexeme_meanings.lexeme_id
                          AND l.owner_user_id = ?
                      )
                    LIMIT 1
                    """,
                (lexeme_id, meaning_key, self._owner_user_id),
            ).fetchone()

            inserted = False
            if row is None:
                cursor = conn.execute(
                    """
                    INSERT INTO lexeme_meanings (
                        lexeme_id,
                        meaning_key,
                        cor_lemma_idx,
                        dictionary_status,
                        gloss,
                        english_translation,
                        pos_tag,
                        morphology
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        lexeme_id,
                        meaning_key,
                        cor_lemma_idx,
                        dictionary_status,
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
                        dictionary_status,
                        gloss,
                        english_translation,
                        pos_tag,
                        morphology,
                        lexeme_id
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
                        dictionary_status = CASE
                            WHEN dictionary_status = 'cor' OR ? = 'cor' THEN 'cor'
                            WHEN dictionary_status = 'generated_non_cor' OR ? = 'generated_non_cor' THEN 'generated_non_cor'
                            ELSE 'unknown'
                        END,
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
                        dictionary_status,
                        dictionary_status,
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
                        dictionary_status,
                        gloss,
                        english_translation,
                        pos_tag,
                        morphology,
                        lexeme_id
                    FROM lexeme_meanings
                    WHERE id = ?
                    LIMIT 1
                    """,
                    (int(row["id"]),),
                ).fetchone()
        if row is None:
            raise RuntimeError("Failed to create or load lexeme meaning")
        return lexeme_meaning_from_row(row), inserted

    def upsert_lexeme_meaning_by_key(
        self,
        *,
        lexeme_id: int,
        meaning_key: str,
        cor_lemma_idx: int | None,
        dictionary_status: str = "unknown",
        gloss: str | None,
        english_translation: str | None,
        pos_tag: str | None,
        morphology: str | None,
    ) -> tuple[LexemeMeaningRecord, bool]:
        from app.db.repositories.wordbank_meaning_key_upsert import (
            upsert_lexeme_meaning_by_key as _upsert,
        )

        return _upsert(
            db_path=self._db_path,
            owner_user_id=self._owner_user_id,
            lexeme_id=lexeme_id,
            meaning_key=meaning_key,
            cor_lemma_idx=cor_lemma_idx,
            dictionary_status=dictionary_status,
            gloss=gloss,
            english_translation=english_translation,
            pos_tag=pos_tag,
            morphology=morphology,
        )

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
                        pos_tag,
                        preferred_cor_id
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        owner_lexeme_id,
                        item.relation_type,
                        item.sort_order,
                        item.related_lemma,
                        item.english_translation,
                        item.pos_tag,
                        item.preferred_cor_id,
                    ),
                )
