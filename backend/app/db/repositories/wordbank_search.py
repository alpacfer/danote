from __future__ import annotations

import sqlite3

_FTS_MIN_QUERY_LENGTH = 3
_FTS_CANDIDATE_MULTIPLIER = 24
_FTS_MIN_CANDIDATES = 96


def search_lemmas(
    conn: sqlite3.Connection,
    normalized_query: str,
    *,
    limit: int,
) -> list[sqlite3.Row]:
    if len(normalized_query) >= _FTS_MIN_QUERY_LENGTH:
        return _search_lemmas_with_fts(conn, normalized_query, limit=limit)
    return _search_lemmas_with_prefix_only(conn, normalized_query, limit=limit)

def _search_lemmas_with_fts(
    conn: sqlite3.Connection,
    normalized_query: str,
    *,
    limit: int,
) -> list[sqlite3.Row]:
    prefix_pattern = f"{normalized_query}%"
    contains_pattern = f"%{normalized_query}%"
    fts_match_query = _build_fts_match_query(normalized_query)
    candidate_limit = max(limit * _FTS_CANDIDATE_MULTIPLIER, _FTS_MIN_CANDIDATES)
    return conn.execute(
        """
        WITH candidate_ids AS (
            SELECT rowid AS lexeme_id
            FROM wordbank_search_fts
            WHERE wordbank_search_fts MATCH ?
            LIMIT ?
        ),
        candidate_lexemes AS (
            SELECT
                l.id,
                l.lemma,
                l.english_translation,
                l.pos_tag,
                l.morphology
            FROM lexemes l
            JOIN candidate_ids c ON c.lexeme_id = l.id
        ),
        surface_counts AS (
            SELECT sf.lexeme_id, COUNT(*) AS variation_count
            FROM surface_forms sf
            JOIN candidate_ids c ON c.lexeme_id = sf.lexeme_id
            GROUP BY sf.lexeme_id
        ),
        surface_matches AS (
            SELECT
                sf.lexeme_id,
                sf.form,
                sf.pos_tag,
                sf.morphology,
                CASE WHEN sf.form = ? COLLATE NOCASE THEN 1 ELSE 0 END AS has_surface_exact_match,
                CASE WHEN sf.form LIKE ? COLLATE NOCASE THEN 1 ELSE 0 END AS has_surface_prefix_match,
                ROW_NUMBER() OVER (
                    PARTITION BY sf.lexeme_id
                    ORDER BY
                        CASE
                            WHEN sf.form = ? COLLATE NOCASE THEN 0
                            WHEN sf.form LIKE ? COLLATE NOCASE THEN 1
                            ELSE 2
                        END,
                        sf.form COLLATE NOCASE
                ) AS row_number
            FROM surface_forms sf
            JOIN candidate_ids c ON c.lexeme_id = sf.lexeme_id
            WHERE sf.form LIKE ? COLLATE NOCASE
        ),
        best_surface_matches AS (
            SELECT
                lexeme_id,
                form AS match_surface,
                pos_tag,
                morphology,
                has_surface_exact_match,
                has_surface_prefix_match
            FROM surface_matches
            WHERE row_number = 1
        )
        SELECT
            cl.lemma,
            cl.english_translation,
            COALESCE(bsm.pos_tag, cl.pos_tag) AS pos_tag,
            COALESCE(bsm.morphology, cl.morphology) AS morphology,
            COALESCE(sc.variation_count, 0) AS variation_count,
            bsm.match_surface
        FROM candidate_lexemes cl
        LEFT JOIN surface_counts sc ON sc.lexeme_id = cl.id
        LEFT JOIN best_surface_matches bsm ON bsm.lexeme_id = cl.id
        ORDER BY
            CASE
                WHEN cl.lemma = ? COLLATE NOCASE THEN 0
                WHEN COALESCE(bsm.has_surface_exact_match, 0) = 1 THEN 1
                WHEN cl.lemma LIKE ? COLLATE NOCASE THEN 2
                WHEN COALESCE(bsm.has_surface_prefix_match, 0) = 1 THEN 3
                WHEN COALESCE(cl.english_translation, '') LIKE ? COLLATE NOCASE THEN 4
                ELSE 5
            END,
            cl.lemma COLLATE NOCASE
        LIMIT ?
        """,
        (
            fts_match_query,
            candidate_limit,
            normalized_query,
            prefix_pattern,
            normalized_query,
            prefix_pattern,
            contains_pattern,
            normalized_query,
            prefix_pattern,
            prefix_pattern,
            limit,
        ),
    ).fetchall()


def _search_lemmas_with_prefix_only(
    conn: sqlite3.Connection,
    normalized_query: str,
    *,
    limit: int,
) -> list[sqlite3.Row]:
    prefix_pattern = f"{normalized_query}%"
    return conn.execute(
        """
        WITH candidate_ids AS (
            SELECT id AS lexeme_id
            FROM lexemes
            WHERE lemma = ? COLLATE NOCASE
            UNION
            SELECT id AS lexeme_id
            FROM lexemes
            WHERE lemma LIKE ? COLLATE NOCASE
            UNION
            SELECT id AS lexeme_id
            FROM lexemes
            WHERE COALESCE(english_translation, '') LIKE ? COLLATE NOCASE
            UNION
            SELECT lexeme_id
            FROM surface_forms
            WHERE form = ? COLLATE NOCASE
            UNION
            SELECT lexeme_id
            FROM surface_forms
            WHERE form LIKE ? COLLATE NOCASE
        ),
        candidate_lexemes AS (
            SELECT
                l.id,
                l.lemma,
                l.english_translation,
                l.pos_tag,
                l.morphology
            FROM lexemes l
            JOIN candidate_ids c ON c.lexeme_id = l.id
        ),
        surface_counts AS (
            SELECT sf.lexeme_id, COUNT(*) AS variation_count
            FROM surface_forms sf
            JOIN candidate_ids c ON c.lexeme_id = sf.lexeme_id
            GROUP BY sf.lexeme_id
        ),
        surface_matches AS (
            SELECT
                sf.lexeme_id,
                sf.form,
                sf.pos_tag,
                sf.morphology,
                CASE WHEN sf.form = ? COLLATE NOCASE THEN 1 ELSE 0 END AS has_surface_exact_match,
                CASE WHEN sf.form LIKE ? COLLATE NOCASE THEN 1 ELSE 0 END AS has_surface_prefix_match,
                ROW_NUMBER() OVER (
                    PARTITION BY sf.lexeme_id
                    ORDER BY
                        CASE
                            WHEN sf.form = ? COLLATE NOCASE THEN 0
                            WHEN sf.form LIKE ? COLLATE NOCASE THEN 1
                            ELSE 2
                        END,
                        sf.form COLLATE NOCASE
                ) AS row_number
            FROM surface_forms sf
            JOIN candidate_ids c ON c.lexeme_id = sf.lexeme_id
            WHERE sf.form = ? COLLATE NOCASE OR sf.form LIKE ? COLLATE NOCASE
        ),
        best_surface_matches AS (
            SELECT
                lexeme_id,
                form AS match_surface,
                pos_tag,
                morphology,
                has_surface_exact_match,
                has_surface_prefix_match
            FROM surface_matches
            WHERE row_number = 1
        )
        SELECT
            cl.lemma,
            cl.english_translation,
            COALESCE(bsm.pos_tag, cl.pos_tag) AS pos_tag,
            COALESCE(bsm.morphology, cl.morphology) AS morphology,
            COALESCE(sc.variation_count, 0) AS variation_count,
            bsm.match_surface
        FROM candidate_lexemes cl
        LEFT JOIN surface_counts sc ON sc.lexeme_id = cl.id
        LEFT JOIN best_surface_matches bsm ON bsm.lexeme_id = cl.id
        ORDER BY
            CASE
                WHEN cl.lemma = ? COLLATE NOCASE THEN 0
                WHEN COALESCE(bsm.has_surface_exact_match, 0) = 1 THEN 1
                WHEN cl.lemma LIKE ? COLLATE NOCASE THEN 2
                WHEN COALESCE(bsm.has_surface_prefix_match, 0) = 1 THEN 3
                WHEN COALESCE(cl.english_translation, '') LIKE ? COLLATE NOCASE THEN 4
                ELSE 5
            END,
            cl.lemma COLLATE NOCASE
        LIMIT ?
        """,
        (
            normalized_query,
            prefix_pattern,
            prefix_pattern,
            normalized_query,
            prefix_pattern,
            normalized_query,
            prefix_pattern,
            normalized_query,
            prefix_pattern,
            normalized_query,
            prefix_pattern,
            normalized_query,
            prefix_pattern,
            prefix_pattern,
            limit,
        ),
    ).fetchall()


def _build_fts_match_query(normalized_query: str) -> str:
    escaped_query = normalized_query.replace('"', '""')
    return f'"{escaped_query}"'
