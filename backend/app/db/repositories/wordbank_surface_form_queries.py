from __future__ import annotations


def select_surface_form_row(conn, *, lexeme_id: int, meaning_id: int | None, form: str):
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
