from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.db.sqlite import get_connection, timed_db_operation


@dataclass(frozen=True, slots=True)
class LemmaListRow:
    lemma: str
    english_translation: str | None
    pos_tag: str | None
    variation_count: int


@dataclass(frozen=True, slots=True)
class WordbankSearchRow:
    lemma: str
    english_translation: str | None
    pos_tag: str | None
    morphology: str | None
    variation_count: int
    match_surface: str | None


@dataclass(frozen=True, slots=True)
class LexemeRecord:
    id: int
    lemma: str
    english_translation: str | None
    pos_tag: str | None
    morphology: str | None


@dataclass(frozen=True, slots=True)
class SurfaceFormRecord:
    form: str
    english_translation: str | None
    pos_tag: str | None
    morphology: str | None
    has_pronunciation: bool


class WordbankRepository:
    def __init__(self, db_path: Path):
        self._db_path = db_path

    def list_lemmas(self) -> list[LemmaListRow]:
        with timed_db_operation("wordbank.list_lemmas"), get_connection(self._db_path, read_only=True) as conn:
            rows = conn.execute(
                """
                SELECT
                    l.lemma,
                    l.english_translation AS english_translation,
                    l.pos_tag AS pos_tag,
                    COUNT(sf.id) AS variation_count
                FROM lexemes l
                LEFT JOIN surface_forms sf ON sf.lexeme_id = l.id
                GROUP BY l.id, l.lemma
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
        contains_pattern = f"%{normalized_query}%"
        prefix_pattern = f"{normalized_query}%"
        with timed_db_operation("wordbank.search_lemmas"), get_connection(self._db_path, read_only=True) as conn:
            rows = conn.execute(
                """
                WITH search_candidates AS (
                    SELECT
                        l.id AS lexeme_id,
                        l.lemma AS lemma,
                        l.english_translation AS english_translation,
                        l.pos_tag AS pos_tag,
                        l.morphology AS morphology,
                        (
                            SELECT COUNT(*)
                            FROM surface_forms sf_all
                            WHERE sf_all.lexeme_id = l.id
                        ) AS variation_count,
                        (
                            SELECT sf_match.form
                            FROM surface_forms sf_match
                            WHERE
                                sf_match.lexeme_id = l.id
                                AND sf_match.form LIKE ? COLLATE NOCASE
                            ORDER BY
                                CASE
                                    WHEN sf_match.form = ? COLLATE NOCASE THEN 0
                                    WHEN sf_match.form LIKE ? COLLATE NOCASE THEN 1
                                    ELSE 2
                                END,
                                sf_match.form COLLATE NOCASE
                            LIMIT 1
                        ) AS match_surface,
                        (
                            SELECT sf_match.pos_tag
                            FROM surface_forms sf_match
                            WHERE
                                sf_match.lexeme_id = l.id
                                AND sf_match.form LIKE ? COLLATE NOCASE
                            ORDER BY
                                CASE
                                    WHEN sf_match.form = ? COLLATE NOCASE THEN 0
                                    WHEN sf_match.form LIKE ? COLLATE NOCASE THEN 1
                                    ELSE 2
                                END,
                                sf_match.form COLLATE NOCASE
                            LIMIT 1
                        ) AS match_surface_pos_tag,
                        (
                            SELECT sf_match.morphology
                            FROM surface_forms sf_match
                            WHERE
                                sf_match.lexeme_id = l.id
                                AND sf_match.form LIKE ? COLLATE NOCASE
                            ORDER BY
                                CASE
                                    WHEN sf_match.form = ? COLLATE NOCASE THEN 0
                                    WHEN sf_match.form LIKE ? COLLATE NOCASE THEN 1
                                    ELSE 2
                                END,
                                sf_match.form COLLATE NOCASE
                            LIMIT 1
                        ) AS match_surface_morphology,
                        EXISTS(
                            SELECT 1
                            FROM surface_forms sf_exact
                            WHERE
                                sf_exact.lexeme_id = l.id
                                AND sf_exact.form = ? COLLATE NOCASE
                        ) AS has_surface_exact_match,
                        EXISTS(
                            SELECT 1
                            FROM surface_forms sf_prefix
                            WHERE
                                sf_prefix.lexeme_id = l.id
                                AND sf_prefix.form LIKE ? COLLATE NOCASE
                        ) AS has_surface_prefix_match
                    FROM lexemes l
                    WHERE
                        l.lemma LIKE ? COLLATE NOCASE
                        OR COALESCE(l.english_translation, '') LIKE ? COLLATE NOCASE
                        OR EXISTS(
                            SELECT 1
                            FROM surface_forms sf_contains
                            WHERE
                                sf_contains.lexeme_id = l.id
                                AND sf_contains.form LIKE ? COLLATE NOCASE
                        )
                )
                SELECT
                    lemma,
                    english_translation,
                    COALESCE(match_surface_pos_tag, pos_tag) AS pos_tag,
                    COALESCE(match_surface_morphology, morphology) AS morphology,
                    variation_count,
                    match_surface,
                    has_surface_exact_match,
                    has_surface_prefix_match
                FROM search_candidates
                ORDER BY
                    CASE
                        WHEN lemma = ? COLLATE NOCASE THEN 0
                        WHEN has_surface_exact_match = 1 THEN 1
                        WHEN lemma LIKE ? COLLATE NOCASE THEN 2
                        WHEN has_surface_prefix_match = 1 THEN 3
                        WHEN COALESCE(english_translation, '') LIKE ? COLLATE NOCASE THEN 4
                        ELSE 5
                    END,
                    lemma COLLATE NOCASE
                LIMIT ?
                """,
                (
                    contains_pattern,
                    normalized_query,
                    prefix_pattern,
                    contains_pattern,
                    normalized_query,
                    prefix_pattern,
                    contains_pattern,
                    normalized_query,
                    prefix_pattern,
                    normalized_query,
                    prefix_pattern,
                    contains_pattern,
                    contains_pattern,
                    contains_pattern,
                    normalized_query,
                    prefix_pattern,
                    prefix_pattern,
                    limit,
                ),
            ).fetchall()

        return [
            WordbankSearchRow(
                lemma=str(row["lemma"]),
                english_translation=row["english_translation"],
                pos_tag=row["pos_tag"],
                morphology=row["morphology"],
                variation_count=int(row["variation_count"]),
                match_surface=row["match_surface"],
            )
            for row in rows
        ]

    def get_lexeme(self, normalized_lemma: str) -> LexemeRecord | None:
        with timed_db_operation("wordbank.get_lexeme"), get_connection(self._db_path, read_only=True) as conn:
            row = conn.execute(
                """
                SELECT id, lemma, english_translation AS english_translation, pos_tag, morphology
                FROM lexemes
                WHERE lemma = ?
                """,
                (normalized_lemma,),
            ).fetchone()
        if row is None:
            return None
        return LexemeRecord(
            id=int(row["id"]),
            lemma=str(row["lemma"]),
            english_translation=row["english_translation"],
            pos_tag=row["pos_tag"],
            morphology=row["morphology"],
        )

    def list_surface_forms(self, lexeme_id: int) -> list[SurfaceFormRecord]:
        with timed_db_operation("wordbank.list_surface_forms"), get_connection(self._db_path, read_only=True) as conn:
            rows = conn.execute(
                """
                SELECT
                    form,
                    english_translation AS english_translation,
                    pos_tag,
                    morphology,
                    CASE WHEN pronunciation_audio IS NOT NULL THEN 1 ELSE 0 END AS has_pronunciation
                FROM surface_forms
                WHERE lexeme_id = ?
                ORDER BY form COLLATE NOCASE
                """,
                (lexeme_id,),
            ).fetchall()
        return [
            SurfaceFormRecord(
                form=str(row["form"]),
                english_translation=row["english_translation"],
                pos_tag=row["pos_tag"],
                morphology=row["morphology"],
                has_pronunciation=bool(row["has_pronunciation"]),
            )
            for row in rows
        ]

    def update_lexeme_metadata(self, *, lexeme_id: int, pos_tag: str | None, morphology: str | None) -> None:
        with timed_db_operation("wordbank.update_lexeme_metadata"), get_connection(self._db_path) as conn:
            conn.execute(
                "UPDATE lexemes SET pos_tag = ?, morphology = ? WHERE id = ?",
                (pos_tag, morphology, lexeme_id),
            )

    def update_surface_form_metadata(
        self,
        *,
        lexeme_id: int,
        form: str,
        pos_tag: str | None,
        morphology: str | None,
    ) -> None:
        with timed_db_operation("wordbank.update_surface_form_metadata"), get_connection(self._db_path) as conn:
            conn.execute(
                "UPDATE surface_forms SET pos_tag = ?, morphology = ? WHERE lexeme_id = ? AND form = ?",
                (pos_tag, morphology, lexeme_id, form),
            )

    def insert_or_load_lexeme(
        self,
        *,
        stored_lemma: str,
        translation: str | None,
        provider: str | None,
        pos_tag: str | None,
        morphology: str | None,
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
                    "manual",
                    translation,
                    provider if translation else None,
                    pos_tag,
                    morphology,
                ),
            )
            lexeme_row = conn.execute(
                "SELECT id FROM lexemes WHERE lemma = ?",
                (stored_lemma,),
            ).fetchone()
            if lexeme_row is None:
                raise RuntimeError("Failed to create or load lexeme")
            lexeme_id = int(lexeme_row["id"])
            if translation:
                conn.execute(
                    """
                    UPDATE lexemes
                    SET english_translation = ?, translation_provider = ?
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
        form: str,
        translation: str | None,
        provider: str | None,
        pos_tag: str | None,
        morphology: str | None,
    ) -> bool:
        with timed_db_operation("wordbank.insert_or_update_surface_form"), get_connection(self._db_path) as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO surface_forms (
                    lexeme_id,
                    form,
                    source,
                    english_translation,
                    translation_provider,
                    pos_tag,
                    morphology
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    lexeme_id,
                    form,
                    "manual",
                    translation,
                    provider if translation else None,
                    pos_tag,
                    morphology,
                ),
            )
            if translation:
                conn.execute(
                    """
                    UPDATE surface_forms
                    SET english_translation = ?, translation_provider = ?
                    WHERE lexeme_id = ? AND form = ?
                    """,
                    (translation, provider, lexeme_id, form),
                )
            conn.execute(
                """
                UPDATE surface_forms
                SET seen_count = seen_count + 1,
                    last_seen_at = CURRENT_TIMESTAMP
                WHERE lexeme_id = ? AND form = ?
                """,
                (lexeme_id, form),
            )
            conn.execute(
                """
                UPDATE surface_forms
                SET pos_tag = COALESCE(pos_tag, ?),
                    morphology = COALESCE(morphology, ?)
                WHERE lexeme_id = ? AND form = ?
                """,
                (pos_tag, morphology, lexeme_id, form),
            )
        return cursor.rowcount == 1
