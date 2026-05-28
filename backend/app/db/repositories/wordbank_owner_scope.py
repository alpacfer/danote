from __future__ import annotations


def lexeme_scope_exists(conn, lexeme_id: int, *, owner_user_id: int) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM lexemes WHERE id = ? AND owner_user_id = ? LIMIT 1",
            (lexeme_id, owner_user_id),
        ).fetchone()
        is not None
    )


def meaning_scope_exists(conn, *, lexeme_id: int, meaning_id: int, owner_user_id: int) -> bool:
    return (
        conn.execute(
            """
            SELECT 1
            FROM lexeme_meanings lm
            JOIN lexemes l ON l.id = lm.lexeme_id
            WHERE lm.id = ? AND lm.lexeme_id = ? AND l.owner_user_id = ?
            LIMIT 1
            """,
            (meaning_id, lexeme_id, owner_user_id),
        ).fetchone()
        is not None
    )


def surface_form_scope_exists(conn, surface_form_id: int, *, owner_user_id: int) -> bool:
    return (
        conn.execute(
            """
            SELECT 1
            FROM surface_forms sf
            JOIN lexemes l ON l.id = sf.lexeme_id
            WHERE sf.id = ? AND l.owner_user_id = ?
            LIMIT 1
            """,
            (surface_form_id, owner_user_id),
        ).fetchone()
        is not None
    )
