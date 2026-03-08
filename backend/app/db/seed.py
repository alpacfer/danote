from __future__ import annotations

from pathlib import Path

from app.db.migrations import get_connection

STARTER_LEXEMES: dict[str, dict[str, list[str] | str]] = {
    # Keep starter forms lean: base forms as exact-known entries.
    "bog": {"source": "manual", "forms": ["bog"]},
    "kan": {"source": "manual", "forms": ["kan"]},
    "lide": {"source": "manual", "forms": ["lide"]},
}


def seed_starter_data(db_path: Path) -> dict[str, int]:
    inserted_lexemes = 0
    inserted_surface_forms = 0

    with get_connection(db_path) as conn:
        for lemma, payload in STARTER_LEXEMES.items():
            source = str(payload["source"])
            forms = list(payload["forms"])

            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO lexemes (lemma, source)
                VALUES (?, ?)
                """,
                (lemma, source),
            )
            inserted_lexemes += 1 if cursor.rowcount == 1 else 0

            lexeme_row = conn.execute(
                "SELECT id FROM lexemes WHERE lemma = ?",
                (lemma,),
            ).fetchone()
            if lexeme_row is None:
                continue

            lexeme_id = lexeme_row["id"]
            conn.execute(
                """
                INSERT OR IGNORE INTO lexeme_meanings (
                    lexeme_id,
                    meaning_key
                )
                VALUES (?, ?)
                """,
                (lexeme_id, lemma),
            )
            meaning_row = conn.execute(
                """
                SELECT id
                FROM lexeme_meanings
                WHERE lexeme_id = ? AND meaning_key = ?
                LIMIT 1
                """,
                (lexeme_id, lemma),
            ).fetchone()
            if meaning_row is None:
                continue
            meaning_id = meaning_row["id"]

            placeholders = ", ".join("?" for _ in forms)
            conn.execute(
                f"""
                DELETE FROM surface_forms
                WHERE lexeme_id = ?
                  AND source = 'seed'
                  AND form NOT IN ({placeholders})
                """,
                (lexeme_id, *forms),
            )

            for form in forms:
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO surface_forms (lexeme_id, form, source, meaning_id)
                    VALUES (?, ?, ?, ?)
                    """,
                    (lexeme_id, form, "seed", meaning_id),
                )
                inserted_surface_forms += 1 if cursor.rowcount == 1 else 0
                conn.execute(
                    """
                    UPDATE surface_forms
                    SET meaning_id = COALESCE(meaning_id, ?)
                    WHERE lexeme_id = ? AND form = ?
                    """,
                    (meaning_id, lexeme_id, form),
                )

    return {
        "inserted_lexemes": inserted_lexemes,
        "inserted_surface_forms": inserted_surface_forms,
    }
