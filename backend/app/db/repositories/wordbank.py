from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.db.repositories.wordbank_search import search_lemmas as search_wordbank_rows
from app.db.sqlite import get_connection, timed_db_operation

_QUERY_COR_IDS_SEPARATOR = "\x1f"


@dataclass(frozen=True, slots=True)
class LemmaListRow:
    lemma: str
    english_translation: str | None
    pos_tag: str | None
    variation_count: int


@dataclass(frozen=True, slots=True)
class WordbankSearchRow:
    lemma: str
    meaning_id: int | None
    meaning_key: str | None
    gloss: str | None
    cor_lemma_idx: int | None
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
class LexemeMeaningRecord:
    id: int
    meaning_key: str
    cor_lemma_idx: int | None
    gloss: str | None
    english_translation: str | None
    pos_tag: str | None
    morphology: str | None


@dataclass(frozen=True, slots=True)
class SurfaceFormRecord:
    id: int
    lexeme_id: int
    form: str
    english_translation: str | None
    pos_tag: str | None
    morphology: str | None
    meaning_id: int | None
    has_pronunciation: bool


class WordbankRepository:
    def __init__(self, db_path: Path):
        self._db_path = db_path

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
                query_cor_ids=_parse_query_cor_ids(row["query_cor_ids"]),
            )
            for row in rows
        ]

    def get_lexeme(self, normalized_lemma: str) -> LexemeRecord | None:
        with timed_db_operation("wordbank.get_lexeme"), get_connection(
            self._db_path, read_only=True
        ) as conn:
            row = conn.execute(
                """
                SELECT id, lemma, english_translation, pos_tag, morphology
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
            english_translation=row["english_translation"],
            pos_tag=row["pos_tag"],
            morphology=row["morphology"],
        )

    def list_surface_forms(self, lexeme_id: int) -> list[SurfaceFormRecord]:
        with timed_db_operation("wordbank.list_surface_forms"), get_connection(
            self._db_path, read_only=True
        ) as conn:
            rows = conn.execute(
                """
                SELECT
                    id,
                    lexeme_id,
                    form,
                    english_translation,
                    pos_tag,
                    morphology,
                    meaning_id,
                    CASE WHEN pronunciation_audio IS NOT NULL THEN 1 ELSE 0 END AS has_pronunciation
                FROM surface_forms
                WHERE lexeme_id = ?
                ORDER BY form COLLATE NOCASE, meaning_id ASC, id ASC
                """,
                (lexeme_id,),
            ).fetchall()
        return [_surface_form_from_row(row) for row in rows]

    def find_surface_forms(self, *, lexeme_id: int, form: str) -> list[SurfaceFormRecord]:
        with timed_db_operation("wordbank.find_surface_forms"), get_connection(
            self._db_path, read_only=True
        ) as conn:
            rows = conn.execute(
                """
                SELECT
                    id,
                    lexeme_id,
                    form,
                    english_translation,
                    pos_tag,
                    morphology,
                    meaning_id,
                    CASE WHEN pronunciation_audio IS NOT NULL THEN 1 ELSE 0 END AS has_pronunciation
                FROM surface_forms
                WHERE lexeme_id = ? AND form = ?
                ORDER BY meaning_id ASC, id ASC
                """,
                (lexeme_id, form),
            ).fetchall()
        return [_surface_form_from_row(row) for row in rows]

    def find_surface_form_by_cor_id(self, cor_id: str) -> SurfaceFormRecord | None:
        with timed_db_operation("wordbank.find_surface_form_by_cor_id"), get_connection(
            self._db_path, read_only=True
        ) as conn:
            row = conn.execute(
                """
                SELECT
                    sf.id,
                    sf.lexeme_id,
                    sf.form,
                    sf.english_translation,
                    sf.pos_tag,
                    sf.morphology,
                    sf.meaning_id,
                    CASE WHEN sf.pronunciation_audio IS NOT NULL THEN 1 ELSE 0 END AS has_pronunciation
                FROM surface_form_cor_variants sfcv
                JOIN surface_forms sf ON sf.id = sfcv.surface_form_id
                WHERE sfcv.cor_id = ?
                ORDER BY sf.id ASC
                LIMIT 1
                """,
                (cor_id,),
            ).fetchone()
        return _surface_form_from_row(row) if row is not None else None

    def list_lexeme_meanings(self, lexeme_id: int) -> list[LexemeMeaningRecord]:
        with timed_db_operation("wordbank.list_lexeme_meanings"), get_connection(
            self._db_path, read_only=True
        ) as conn:
            rows = conn.execute(
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
                WHERE lexeme_id = ?
                ORDER BY id ASC
                """,
                (lexeme_id,),
            ).fetchall()
        return [_lexeme_meaning_from_row(row) for row in rows]

    def get_lexeme_meaning(self, meaning_id: int) -> LexemeMeaningRecord | None:
        with timed_db_operation("wordbank.get_lexeme_meaning"), get_connection(
            self._db_path, read_only=True
        ) as conn:
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
                (meaning_id,),
            ).fetchone()
        return _lexeme_meaning_from_row(row) if row is not None else None

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
        translation: str | None,
        provider: str | None,
        pos_tag: str | None,
        morphology: str | None,
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
                        english_translation,
                        translation_provider,
                        pos_tag,
                        morphology,
                        seen_count,
                        last_seen_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (
                        lexeme_id,
                        meaning_id,
                        form,
                        "manual",
                        translation,
                        provider if translation else None,
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
                        english_translation,
                        pos_tag,
                        morphology,
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
                        english_translation = COALESCE(english_translation, ?),
                        translation_provider = COALESCE(translation_provider, ?),
                        pos_tag = COALESCE(pos_tag, ?),
                        morphology = COALESCE(morphology, ?)
                    WHERE id = ?
                    """,
                    (translation, provider if translation else None, pos_tag, morphology, int(row["id"])),
                )
                row = conn.execute(
                    """
                    SELECT
                        id,
                        lexeme_id,
                        form,
                        english_translation,
                        pos_tag,
                        morphology,
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
        return _surface_form_from_row(row), inserted

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
        return _lexeme_meaning_from_row(row), inserted

    def has_non_verb_forms_without_meaning(self) -> bool:
        with timed_db_operation("wordbank.has_non_verb_forms_without_meaning"), get_connection(
            self._db_path, read_only=True
        ) as conn:
            row = conn.execute(
                """
                SELECT 1
                FROM surface_forms sf
                JOIN lexemes l ON l.id = sf.lexeme_id
                WHERE sf.meaning_id IS NULL
                  AND COALESCE(UPPER(l.pos_tag), '') NOT IN ('VERB', 'AUX')
                LIMIT 1
                """
            ).fetchone()
        return row is not None


def _surface_form_from_row(row) -> SurfaceFormRecord:
    return SurfaceFormRecord(
        id=int(row["id"]),
        lexeme_id=int(row["lexeme_id"]),
        form=str(row["form"]),
        english_translation=row["english_translation"],
        pos_tag=row["pos_tag"],
        morphology=row["morphology"],
        meaning_id=int(row["meaning_id"]) if row["meaning_id"] is not None else None,
        has_pronunciation=bool(row["has_pronunciation"]),
    )


def _lexeme_meaning_from_row(row) -> LexemeMeaningRecord:
    return LexemeMeaningRecord(
        id=int(row["id"]),
        meaning_key=str(row["meaning_key"]),
        cor_lemma_idx=int(row["cor_lemma_idx"]) if row["cor_lemma_idx"] is not None else None,
        gloss=row["gloss"],
        english_translation=row["english_translation"],
        pos_tag=row["pos_tag"],
        morphology=row["morphology"],
    )


def _select_surface_form_row(conn, *, lexeme_id: int, meaning_id: int | None, form: str):
    if meaning_id is None:
        return conn.execute(
            """
            SELECT
                id,
                lexeme_id,
                form,
                english_translation,
                pos_tag,
                morphology,
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
            english_translation,
            pos_tag,
            morphology,
            meaning_id,
            CASE WHEN pronunciation_audio IS NOT NULL THEN 1 ELSE 0 END AS has_pronunciation
        FROM surface_forms
        WHERE meaning_id = ? AND form = ?
        LIMIT 1
        """,
        (meaning_id, form),
    ).fetchone()


def _parse_query_cor_ids(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [item for item in raw.split(_QUERY_COR_IDS_SEPARATOR) if item]
