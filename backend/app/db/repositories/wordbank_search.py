from __future__ import annotations

import sqlite3

_SHORT_QUERY_MIN_LENGTH = 3


def search_lemmas(
    conn: sqlite3.Connection,
    normalized_query: str,
    *,
    limit: int,
) -> list[sqlite3.Row]:
    params = {
        "exact_query": normalized_query,
        "prefix_pattern": f"{normalized_query}%",
        "contains_pattern": f"%{normalized_query}%",
        "limit": limit,
    }
    if len(normalized_query) >= _SHORT_QUERY_MIN_LENGTH:
        return conn.execute(_search_sql(include_contains=True), params).fetchall()
    return conn.execute(_search_sql(include_contains=False), params).fetchall()


def _search_sql(*, include_contains: bool) -> str:
    surface_match_filter = """
        sf.form = :exact_query COLLATE NOCASE
        OR sf.form LIKE :prefix_pattern COLLATE NOCASE
    """
    nonverb_filter = """
        l.lemma = :exact_query COLLATE NOCASE
        OR l.lemma LIKE :prefix_pattern COLLATE NOCASE
        OR COALESCE(lm.english_translation, '') LIKE :prefix_pattern COLLATE NOCASE
        OR COALESCE(lm.gloss, '') LIKE :prefix_pattern COLLATE NOCASE
        OR EXISTS (
            SELECT 1
            FROM surface_forms sf
            WHERE sf.meaning_id = lm.id
              AND ({surface_match_filter})
        )
    """
    verb_filter = """
        l.lemma = :exact_query COLLATE NOCASE
        OR l.lemma LIKE :prefix_pattern COLLATE NOCASE
        OR COALESCE(l.english_translation, '') LIKE :prefix_pattern COLLATE NOCASE
        OR EXISTS (
            SELECT 1
            FROM surface_forms sf
            WHERE sf.lexeme_id = l.id
              AND sf.meaning_id IS NULL
              AND ({surface_match_filter})
        )
    """
    if include_contains:
        surface_match_filter = """
            sf.form = :exact_query COLLATE NOCASE
            OR sf.form LIKE :prefix_pattern COLLATE NOCASE
            OR sf.form LIKE :contains_pattern COLLATE NOCASE
        """
        nonverb_filter = """
            l.lemma = :exact_query COLLATE NOCASE
            OR l.lemma LIKE :prefix_pattern COLLATE NOCASE
            OR l.lemma LIKE :contains_pattern COLLATE NOCASE
            OR COALESCE(lm.english_translation, '') LIKE :contains_pattern COLLATE NOCASE
            OR COALESCE(lm.gloss, '') LIKE :contains_pattern COLLATE NOCASE
            OR EXISTS (
                SELECT 1
                FROM surface_forms sf
                WHERE sf.meaning_id = lm.id
                  AND ({surface_match_filter})
            )
        """
        verb_filter = """
            l.lemma = :exact_query COLLATE NOCASE
            OR l.lemma LIKE :prefix_pattern COLLATE NOCASE
            OR l.lemma LIKE :contains_pattern COLLATE NOCASE
            OR COALESCE(l.english_translation, '') LIKE :contains_pattern COLLATE NOCASE
            OR EXISTS (
                SELECT 1
                FROM surface_forms sf
                WHERE sf.lexeme_id = l.id
                  AND sf.meaning_id IS NULL
                  AND ({surface_match_filter})
            )
        """

    return f"""
        WITH nonverb_surface_counts AS (
            SELECT meaning_id, COUNT(DISTINCT form) AS variation_count
            FROM surface_forms
            WHERE meaning_id IS NOT NULL
            GROUP BY meaning_id
        ),
        nonverb_surface_matches AS (
            SELECT
                sf.meaning_id,
                sf.form,
                sf.pos_tag,
                sf.morphology,
                CASE WHEN sf.form = :exact_query COLLATE NOCASE THEN 1 ELSE 0 END AS has_surface_exact_match,
                CASE WHEN sf.form LIKE :prefix_pattern COLLATE NOCASE THEN 1 ELSE 0 END AS has_surface_prefix_match,
                ROW_NUMBER() OVER (
                    PARTITION BY sf.meaning_id
                    ORDER BY
                        CASE
                            WHEN sf.form = :exact_query COLLATE NOCASE THEN 0
                            WHEN sf.form LIKE :prefix_pattern COLLATE NOCASE THEN 1
                            ELSE 2
                        END,
                        sf.form COLLATE NOCASE,
                        sf.id ASC
                ) AS row_number
            FROM surface_forms sf
            WHERE sf.meaning_id IS NOT NULL
              AND ({surface_match_filter})
        ),
        nonverb_best_surface_matches AS (
            SELECT
                meaning_id,
                form AS match_surface,
                pos_tag,
                morphology,
                has_surface_exact_match,
                has_surface_prefix_match
            FROM nonverb_surface_matches
            WHERE row_number = 1
        ),
        nonverb_query_cor_ids AS (
            SELECT
                sf.meaning_id,
                GROUP_CONCAT(sfcv.cor_id, char(31)) AS query_cor_ids
            FROM surface_forms sf
            JOIN surface_form_cor_variants sfcv ON sfcv.surface_form_id = sf.id
            WHERE sf.meaning_id IS NOT NULL
              AND sf.form = :exact_query COLLATE NOCASE
            GROUP BY sf.meaning_id
        ),
        verb_surface_counts AS (
            SELECT lexeme_id, COUNT(DISTINCT form) AS variation_count
            FROM surface_forms
            WHERE meaning_id IS NULL
            GROUP BY lexeme_id
        ),
        verb_surface_matches AS (
            SELECT
                sf.lexeme_id,
                sf.form,
                sf.pos_tag,
                sf.morphology,
                CASE WHEN sf.form = :exact_query COLLATE NOCASE THEN 1 ELSE 0 END AS has_surface_exact_match,
                CASE WHEN sf.form LIKE :prefix_pattern COLLATE NOCASE THEN 1 ELSE 0 END AS has_surface_prefix_match,
                ROW_NUMBER() OVER (
                    PARTITION BY sf.lexeme_id
                    ORDER BY
                        CASE
                            WHEN sf.form = :exact_query COLLATE NOCASE THEN 0
                            WHEN sf.form LIKE :prefix_pattern COLLATE NOCASE THEN 1
                            ELSE 2
                        END,
                        sf.form COLLATE NOCASE,
                        sf.id ASC
                ) AS row_number
            FROM surface_forms sf
            WHERE sf.meaning_id IS NULL
              AND ({surface_match_filter})
        ),
        verb_best_surface_matches AS (
            SELECT
                lexeme_id,
                form AS match_surface,
                pos_tag,
                morphology,
                has_surface_exact_match,
                has_surface_prefix_match
            FROM verb_surface_matches
            WHERE row_number = 1
        ),
        verb_query_cor_ids AS (
            SELECT
                sf.lexeme_id,
                GROUP_CONCAT(sfcv.cor_id, char(31)) AS query_cor_ids
            FROM surface_forms sf
            JOIN surface_form_cor_variants sfcv ON sfcv.surface_form_id = sf.id
            WHERE sf.meaning_id IS NULL
              AND sf.form = :exact_query COLLATE NOCASE
            GROUP BY sf.lexeme_id
        ),
        search_units AS (
            SELECT
                l.lemma,
                lm.id AS meaning_id,
                lm.meaning_key,
                lm.gloss,
                lm.cor_lemma_idx,
                lm.english_translation,
                COALESCE(bsm.pos_tag, lm.pos_tag, l.pos_tag) AS pos_tag,
                COALESCE(bsm.morphology, lm.morphology, l.morphology) AS morphology,
                COALESCE(sc.variation_count, 0) AS variation_count,
                bsm.match_surface,
                COALESCE(qc.query_cor_ids, '') AS query_cor_ids,
                CASE
                    WHEN l.lemma = :exact_query COLLATE NOCASE THEN 0
                    WHEN COALESCE(bsm.has_surface_exact_match, 0) = 1 THEN 1
                    WHEN l.lemma LIKE :prefix_pattern COLLATE NOCASE THEN 2
                    WHEN COALESCE(bsm.has_surface_prefix_match, 0) = 1 THEN 3
                    WHEN COALESCE(lm.english_translation, '') LIKE :prefix_pattern COLLATE NOCASE THEN 4
                    WHEN COALESCE(lm.gloss, '') LIKE :prefix_pattern COLLATE NOCASE THEN 5
                    ELSE 6
                END AS sort_rank
            FROM lexeme_meanings lm
            JOIN lexemes l ON l.id = lm.lexeme_id
            LEFT JOIN nonverb_surface_counts sc ON sc.meaning_id = lm.id
            LEFT JOIN nonverb_best_surface_matches bsm ON bsm.meaning_id = lm.id
            LEFT JOIN nonverb_query_cor_ids qc ON qc.meaning_id = lm.id
            WHERE ({nonverb_filter.format(surface_match_filter=surface_match_filter)})

            UNION ALL

            SELECT
                l.lemma,
                NULL AS meaning_id,
                NULL AS meaning_key,
                NULL AS gloss,
                NULL AS cor_lemma_idx,
                l.english_translation,
                COALESCE(bsm.pos_tag, l.pos_tag) AS pos_tag,
                COALESCE(bsm.morphology, l.morphology) AS morphology,
                COALESCE(sc.variation_count, 0) AS variation_count,
                bsm.match_surface,
                COALESCE(qc.query_cor_ids, '') AS query_cor_ids,
                CASE
                    WHEN l.lemma = :exact_query COLLATE NOCASE THEN 0
                    WHEN COALESCE(bsm.has_surface_exact_match, 0) = 1 THEN 1
                    WHEN l.lemma LIKE :prefix_pattern COLLATE NOCASE THEN 2
                    WHEN COALESCE(bsm.has_surface_prefix_match, 0) = 1 THEN 3
                    WHEN COALESCE(l.english_translation, '') LIKE :prefix_pattern COLLATE NOCASE THEN 4
                    ELSE 6
                END AS sort_rank
            FROM lexemes l
            LEFT JOIN verb_surface_counts sc ON sc.lexeme_id = l.id
            LEFT JOIN verb_best_surface_matches bsm ON bsm.lexeme_id = l.id
            LEFT JOIN verb_query_cor_ids qc ON qc.lexeme_id = l.id
            WHERE NOT EXISTS (
                SELECT 1
                FROM lexeme_meanings lm
                WHERE lm.lexeme_id = l.id
            )
              AND ({verb_filter.format(surface_match_filter=surface_match_filter)})
        )
        SELECT
            lemma,
            meaning_id,
            meaning_key,
            gloss,
            cor_lemma_idx,
            english_translation,
            pos_tag,
            morphology,
            variation_count,
            match_surface,
            query_cor_ids
        FROM search_units
        ORDER BY sort_rank, lemma COLLATE NOCASE, COALESCE(meaning_id, 0), match_surface COLLATE NOCASE
        LIMIT :limit
    """
