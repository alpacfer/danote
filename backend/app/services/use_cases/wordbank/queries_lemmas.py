from __future__ import annotations

from app.api.schemas.v1.wordbank import LemmaListResponse, LemmaSummary, WordbankSearchItem, WordbankSearchResponse
from app.db.migrations import get_connection
from app.services.token_classifier import normalize_token


class WordbankQueriesLemmasMixin:
    def list_lemmas(self) -> LemmaListResponse:
        with get_connection(self._db_path) as conn:
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

        return LemmaListResponse(
            items=[
                LemmaSummary(
                    lemma=row["lemma"],
                    display_lemma=self._display_lemma_for_list(row["lemma"], row["pos_tag"]),
                    english_translation=row["english_translation"],
                    variation_count=int(row["variation_count"]),
                )
                for row in rows
            ]
        )



    def search_lemmas(self, query: str, *, limit: int = 8) -> WordbankSearchResponse:
        normalized_query = normalize_token(query)
        if not normalized_query:
            raise ValueError("query is required")
        if limit < 1:
            raise ValueError("limit must be at least 1")

        contains_pattern = f"%{normalized_query}%"
        prefix_pattern = f"{normalized_query}%"
        with get_connection(self._db_path) as conn:
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

        return WordbankSearchResponse(
            items=[
                WordbankSearchItem(
                    lemma=row["lemma"],
                    display_lemma=self._display_lemma_for_list(row["lemma"], row["pos_tag"]),
                    english_translation=row["english_translation"],
                    variation_count=int(row["variation_count"]),
                    match_surface=row["match_surface"],
                    pos_tag=row["pos_tag"],
                    morphology=row["morphology"],
                )
                for row in rows
            ]
        )



    def _display_lemma_for_list(self, lemma: str, pos_tag: str | None) -> str:
        if pos_tag is None:
            pos_tag, _morphology = self._extract_pos_and_morphology(lemma)
        if pos_tag in {"VERB", "AUX"}:
            return f"at {lemma}"
        return lemma
