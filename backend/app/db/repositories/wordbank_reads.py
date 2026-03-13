from __future__ import annotations

from pathlib import Path

from app.db.repositories.wordbank_models import (
    LemmaListRow,
    LexemeMeaningRecord,
    LexemeRecord,
    SurfaceFormRecord,
    VerificationRecord,
    WordbankSearchRow,
    lexeme_meaning_from_row,
    parse_query_cor_ids,
    surface_form_from_row,
    verification_record_from_row,
)
from app.db.repositories.wordbank_search import search_lemmas as search_wordbank_rows
from app.db.sqlite import get_connection, timed_db_operation


class WordbankReadRepository:
    _db_path: Path

    def list_lemmas(self) -> list[LemmaListRow]:
        with timed_db_operation("wordbank.list_lemmas"), get_connection(
            self._db_path, read_only=True
        ) as conn:
            rows = conn.execute(
                """
                WITH meaning_counts AS (
                    SELECT lexeme_id, COUNT(*) AS meaning_count
                    FROM lexeme_meanings
                    GROUP BY lexeme_id
                ),
                single_meanings AS (
                    SELECT
                        lm.lexeme_id,
                        lm.english_translation,
                        lm.pos_tag
                    FROM lexeme_meanings lm
                    JOIN meaning_counts mc
                      ON mc.lexeme_id = lm.lexeme_id
                     AND mc.meaning_count = 1
                ),
                surface_counts AS (
                    SELECT
                        sf.lexeme_id,
                        COUNT(DISTINCT CASE WHEN sf.form <> l.lemma THEN sf.form END) AS variation_count
                    FROM surface_forms sf
                    JOIN lexemes l ON l.id = sf.lexeme_id
                    GROUP BY sf.lexeme_id
                )
                SELECT
                    l.lemma,
                    CASE
                        WHEN COALESCE(mc.meaning_count, 0) = 0 THEN l.english_translation
                        WHEN mc.meaning_count = 1 THEN COALESCE(sm.english_translation, l.english_translation)
                        ELSE NULL
                    END AS english_translation,
                    CASE
                        WHEN COALESCE(mc.meaning_count, 0) = 0 THEN l.pos_tag
                        WHEN mc.meaning_count = 1 THEN COALESCE(sm.pos_tag, l.pos_tag)
                        ELSE NULL
                    END AS pos_tag,
                    COALESCE(sc.variation_count, 0) AS variation_count
                FROM lexemes l
                LEFT JOIN meaning_counts mc ON mc.lexeme_id = l.id
                LEFT JOIN single_meanings sm ON sm.lexeme_id = l.id
                LEFT JOIN surface_counts sc ON sc.lexeme_id = l.id
                ORDER BY l.lemma COLLATE NOCASE
                """
            ).fetchall()

        return [
            LemmaListRow(
                lemma=str(row["lemma"]),
                english_translation=row["english_translation"],
                pos_tag=row["pos_tag"],
                variation_count=int(row["variation_count"]),
            )
            for row in rows
        ]

    def search_lemmas(self, normalized_query: str, *, limit: int) -> list[WordbankSearchRow]:
        with timed_db_operation("wordbank.search_lemmas"), get_connection(
            self._db_path, read_only=True
        ) as conn:
            rows = search_wordbank_rows(conn, normalized_query, limit=limit)

        return [
            WordbankSearchRow(
                lemma=str(row["lemma"]),
                meaning_id=int(row["meaning_id"]) if row["meaning_id"] is not None else None,
                meaning_key=row["meaning_key"],
                gloss=row["gloss"],
                cor_lemma_idx=int(row["cor_lemma_idx"]) if row["cor_lemma_idx"] is not None else None,
                english_translation=row["english_translation"],
                pos_tag=row["pos_tag"],
                morphology=row["morphology"],
                variation_count=int(row["variation_count"]),
                match_surface=row["match_surface"],
                query_cor_ids=parse_query_cor_ids(row["query_cor_ids"]),
            )
            for row in rows
        ]

    def get_lexeme(self, normalized_lemma: str) -> LexemeRecord | None:
        with timed_db_operation("wordbank.get_lexeme"), get_connection(
            self._db_path, read_only=True
        ) as conn:
            row = conn.execute(
                """
                SELECT id, lemma, source, english_translation, pos_tag, morphology
                FROM lexemes
                WHERE lemma = ?
                LIMIT 1
                """,
                (normalized_lemma,),
            ).fetchone()
        if row is None:
            return None
        return LexemeRecord(
            id=int(row["id"]),
            lemma=str(row["lemma"]),
            source=str(row["source"]),
            english_translation=row["english_translation"],
            pos_tag=row["pos_tag"],
            morphology=row["morphology"],
        )

    def list_surface_forms(self, lexeme_id: int) -> list[SurfaceFormRecord]:
        with timed_db_operation("wordbank.list_surface_forms"), get_connection(
            self._db_path, read_only=True
        ) as conn:
            rows = conn.execute(
                """SELECT sf.id,sf.lexeme_id,sf.form,sf.source,sf.pos_tag,sf.morphology,
                (SELECT sfcv.cor_id FROM surface_form_cor_variants sfcv WHERE sfcv.surface_form_id = sf.id ORDER BY sfcv.id ASC LIMIT 1) AS cor_id,
                sf.meaning_id, CASE WHEN sf.pronunciation_audio IS NOT NULL THEN 1 ELSE 0 END AS has_pronunciation
                FROM surface_forms sf WHERE sf.lexeme_id = ? ORDER BY sf.form COLLATE NOCASE""",
                (lexeme_id,),
            ).fetchall()
        return [surface_form_from_row(row) for row in rows]

    def find_surface_forms(self, *, lexeme_id: int, form: str) -> list[SurfaceFormRecord]:
        with timed_db_operation("wordbank.find_surface_forms"), get_connection(
            self._db_path, read_only=True
        ) as conn:
            rows = conn.execute(
                """SELECT sf.id,sf.lexeme_id,sf.form,sf.source,sf.pos_tag,sf.morphology,
                (SELECT sfcv.cor_id FROM surface_form_cor_variants sfcv WHERE sfcv.surface_form_id = sf.id ORDER BY sfcv.id ASC LIMIT 1) AS cor_id,
                sf.meaning_id, CASE WHEN sf.pronunciation_audio IS NOT NULL THEN 1 ELSE 0 END AS has_pronunciation
                FROM surface_forms sf WHERE sf.lexeme_id = ? AND sf.form = ? ORDER BY sf.id ASC""",
                (lexeme_id, form),
            ).fetchall()
        return [surface_form_from_row(row) for row in rows]

    def find_surface_form_by_cor_id(self, cor_id: str) -> SurfaceFormRecord | None:
        with timed_db_operation("wordbank.find_surface_form_by_cor_id"), get_connection(
            self._db_path, read_only=True
        ) as conn:
            row = conn.execute(
                """SELECT sf.id,sf.lexeme_id,sf.form,sf.source,sf.pos_tag,sf.morphology,sfcv.cor_id,sf.meaning_id,
                CASE WHEN sf.pronunciation_audio IS NOT NULL THEN 1 ELSE 0 END AS has_pronunciation
                FROM surface_form_cor_variants sfcv JOIN surface_forms sf ON sf.id=sfcv.surface_form_id
                WHERE sfcv.cor_id = ? ORDER BY sfcv.id ASC LIMIT 1""",
                (cor_id,),
            ).fetchone()
        return surface_form_from_row(row) if row is not None else None

    def list_lexeme_meanings(self, lexeme_id: int) -> list[LexemeMeaningRecord]:
        with timed_db_operation("wordbank.list_lexeme_meanings"), get_connection(
            self._db_path, read_only=True
        ) as conn:
            rows = conn.execute(
                """SELECT id,meaning_key,cor_lemma_idx,gloss,english_translation,pos_tag,morphology
                FROM lexeme_meanings WHERE lexeme_id = ? ORDER BY id ASC""",
                (lexeme_id,),
            ).fetchall()
        return [lexeme_meaning_from_row(row) for row in rows]

    def get_lexeme_meaning(self, meaning_id: int) -> LexemeMeaningRecord | None:
        with timed_db_operation("wordbank.get_lexeme_meaning"), get_connection(
            self._db_path, read_only=True
        ) as conn:
            row = conn.execute(
                """SELECT id,meaning_key,cor_lemma_idx,gloss,english_translation,pos_tag,morphology
                FROM lexeme_meanings WHERE id = ? LIMIT 1""",
                (meaning_id,),
            ).fetchone()
        return lexeme_meaning_from_row(row) if row is not None else None

    def list_verification_records(self, lexeme_id: int) -> list[VerificationRecord]:
        with timed_db_operation("wordbank.list_verification_records"), get_connection(
            self._db_path, read_only=True
        ) as conn:
            rows = conn.execute(
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
                    completed_at
                FROM wordbank_verification_records
                WHERE lexeme_id = ?
                ORDER BY meaning_id IS NULL DESC, meaning_id ASC, id ASC
                """,
                (lexeme_id,),
            ).fetchall()
        return [verification_record_from_row(row) for row in rows]

    def get_verification_record(
        self,
        *,
        lexeme_id: int,
        meaning_id: int | None,
    ) -> VerificationRecord | None:
        with timed_db_operation("wordbank.get_verification_record"), get_connection(
            self._db_path, read_only=True
        ) as conn:
            if meaning_id is None:
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
                        completed_at
                    FROM wordbank_verification_records
                    WHERE lexeme_id = ? AND meaning_id IS NULL
                    LIMIT 1
                    """,
                    (lexeme_id,),
                ).fetchone()
            else:
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
                        completed_at
                    FROM wordbank_verification_records
                    WHERE lexeme_id = ? AND meaning_id = ?
                    LIMIT 1
                    """,
                    (lexeme_id, meaning_id),
                ).fetchone()
        return verification_record_from_row(row) if row is not None else None

    def has_non_verb_forms_without_meaning(self) -> bool:
        with timed_db_operation("wordbank.has_non_verb_forms_without_meaning"), get_connection(
            self._db_path, read_only=True
        ) as conn:
            row = conn.execute(
                """SELECT 1 FROM surface_forms sf JOIN lexemes l ON l.id = sf.lexeme_id
                WHERE sf.meaning_id IS NULL AND COALESCE(UPPER(l.pos_tag), '') NOT IN ('VERB', 'AUX') LIMIT 1"""
            ).fetchone()
        return row is not None
