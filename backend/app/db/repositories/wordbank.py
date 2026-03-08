from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.db.repositories.wordbank_search import search_lemmas as search_wordbank_rows
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
    query_cor_ids: list[str]


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
        with timed_db_operation("wordbank.search_lemmas"), get_connection(self._db_path, read_only=True) as conn:
            rows = search_wordbank_rows(conn, normalized_query, limit=limit)

        return [
            WordbankSearchRow(
                lemma=str(row["lemma"]),
                english_translation=row["english_translation"],
                pos_tag=row["pos_tag"],
                morphology=row["morphology"],
                variation_count=int(row["variation_count"]),
                match_surface=row["match_surface"],
                query_cor_ids=_parse_query_cor_ids(row["query_cor_ids"]),
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

    def insert_surface_form_cor_variant(self, *, lexeme_id: int, form: str, cor_id: str) -> bool:
        with timed_db_operation("wordbank.insert_surface_form_cor_variant"), get_connection(self._db_path) as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO surface_form_cor_variants (
                    lexeme_id,
                    form,
                    cor_id
                )
                VALUES (?, ?, ?)
                """,
                (lexeme_id, form, cor_id),
            )
        return cursor.rowcount == 1


_QUERY_COR_IDS_SEPARATOR = "\x1f"


def _parse_query_cor_ids(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [item for item in raw.split(_QUERY_COR_IDS_SEPARATOR) if item]
