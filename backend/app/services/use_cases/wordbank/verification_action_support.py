from __future__ import annotations

import sqlite3

from app.services.token_classifier import normalize_token


def fetch_lexeme_by_lemma(
    conn: sqlite3.Connection,
    lemma: str,
    *,
    owner_user_id: int = 1,
):
    return conn.execute(
        """
        SELECT id, lemma, english_translation, translation_provider, pos_tag, morphology, source
        FROM lexemes
        WHERE owner_user_id = ? AND lemma = ?
        LIMIT 1
        """,
        (owner_user_id, lemma),
    ).fetchone()


def load_requested_meaning(
    conn: sqlite3.Connection,
    *,
    lexeme_id: int,
    meaning_id: int | None,
    normalized_lemma: str,
):
    if meaning_id is None:
        meaning_rows = conn.execute(
            """
            SELECT id, lexeme_id, meaning_key, cor_lemma_idx, gloss, english_translation, pos_tag, morphology
            FROM lexeme_meanings
            WHERE lexeme_id = ?
            ORDER BY id ASC
            LIMIT 2
            """,
            (lexeme_id,),
        ).fetchall()
        if len(meaning_rows) == 1:
            return meaning_rows[0]
        return None
    row = conn.execute(
        """
        SELECT id, lexeme_id, meaning_key, cor_lemma_idx, gloss, english_translation, pos_tag, morphology
        FROM lexeme_meanings
        WHERE id = ? AND lexeme_id = ?
        LIMIT 1
        """,
        (meaning_id, lexeme_id),
    ).fetchone()
    if row is None:
        raise LookupError(f"Meaning '{meaning_id}' was not found for '{normalized_lemma}'")
    return row


def load_meaning_surface(conn: sqlite3.Connection, *, meaning_id: int, form: str):
    return conn.execute(
        "SELECT * FROM surface_forms WHERE meaning_id = ? AND form = ? LIMIT 1",
        (meaning_id, form),
    ).fetchone()


def ensure_target_lexeme(
    conn: sqlite3.Connection,
    *,
    lemma: str,
    english_translation: str | None,
    provider_name: str,
    pos_tag: str | None,
    morphology: str | None,
    owner_user_id: int = 1,
):
    row = fetch_lexeme_by_lemma(conn, lemma, owner_user_id=owner_user_id)
    if row is None:
        conn.execute(
            """
            INSERT INTO lexemes (
                owner_user_id, lemma, source, english_translation, translation_provider, pos_tag, morphology
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                owner_user_id,
                lemma,
                "manual",
                english_translation,
                provider_name if english_translation else None,
                pos_tag,
                morphology,
            ),
        )
        row = fetch_lexeme_by_lemma(conn, lemma, owner_user_id=owner_user_id)
    else:
        conn.execute(
            """
            UPDATE lexemes
            SET english_translation = COALESCE(english_translation, ?),
                translation_provider = COALESCE(translation_provider, ?),
                pos_tag = COALESCE(pos_tag, ?),
                morphology = COALESCE(morphology, ?),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (english_translation, provider_name if english_translation else None, pos_tag, morphology, int(row["id"])),
        )
        row = fetch_lexeme_by_lemma(conn, lemma, owner_user_id=owner_user_id)
    if row is None:
        raise RuntimeError("Failed to create target lexeme")
    return row


def ensure_target_meaning(
    conn: sqlite3.Connection,
    *,
    lexeme_id: int,
    meaning_key: str,
    gloss: str | None,
    english_translation: str | None,
    pos_tag: str | None,
    morphology: str | None,
    cor_lemma_idx: int | None,
):
    row = None
    if cor_lemma_idx is not None:
        row = conn.execute(
            """
            SELECT id, lexeme_id, meaning_key, cor_lemma_idx, gloss, english_translation, pos_tag, morphology
            FROM lexeme_meanings
            WHERE lexeme_id = ? AND cor_lemma_idx = ?
            LIMIT 1
            """,
            (lexeme_id, cor_lemma_idx),
        ).fetchone()
    if row is None:
        row = conn.execute(
            """
            SELECT id, lexeme_id, meaning_key, cor_lemma_idx, gloss, english_translation, pos_tag, morphology
            FROM lexeme_meanings
            WHERE lexeme_id = ? AND meaning_key = ?
            LIMIT 1
            """,
            (lexeme_id, meaning_key),
        ).fetchone()
    if row is None:
        conn.execute(
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
            (lexeme_id, meaning_key, cor_lemma_idx, gloss, english_translation, pos_tag, morphology),
        )
    else:
        conn.execute(
            """
            UPDATE lexeme_meanings
            SET gloss = COALESCE(gloss, ?),
                english_translation = COALESCE(english_translation, ?),
                pos_tag = COALESCE(pos_tag, ?),
                morphology = COALESCE(morphology, ?),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (gloss, english_translation, pos_tag, morphology, int(row["id"])),
        )
    row = conn.execute(
        """
        SELECT id, lexeme_id, meaning_key, cor_lemma_idx, gloss, english_translation, pos_tag, morphology
        FROM lexeme_meanings
        WHERE lexeme_id = ? AND meaning_key = ?
        LIMIT 1
        """,
        (lexeme_id, meaning_key),
    ).fetchone()
    if row is None:
        raise RuntimeError("Failed to create target meaning")
    return row


def ensure_surface_exists(
    conn: sqlite3.Connection,
    *,
    lexeme_id: int,
    meaning_id: int | None,
    form: str,
    pos_tag: str | None,
    morphology: str | None,
) -> None:
    existing = select_surface(conn, lexeme_id=lexeme_id, meaning_id=meaning_id, form=form)
    if existing is None:
        conn.execute(
            """
            INSERT INTO surface_forms (
                lexeme_id,
                meaning_id,
                form,
                source,
                seen_count,
                last_seen_at,
                pos_tag,
                morphology
            )
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?)
            """,
            (lexeme_id, meaning_id, form, "manual", 1, pos_tag, morphology),
        )


def move_or_merge_surface_form(
    conn: sqlite3.Connection,
    *,
    source_surface,
    target_lexeme_id: int,
    target_meaning_id: int | None,
    new_form: str,
) -> int:
    existing = select_surface(conn, lexeme_id=target_lexeme_id, meaning_id=target_meaning_id, form=new_form)
    if existing is None or int(existing["id"]) == int(source_surface["id"]):
        conn.execute(
            """
            UPDATE surface_forms
            SET lexeme_id = ?,
                meaning_id = ?,
                form = ?,
                pos_tag = COALESCE(pos_tag, ?),
                morphology = COALESCE(morphology, ?),
                last_seen_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                target_lexeme_id,
                target_meaning_id,
                new_form,
                source_surface["pos_tag"],
                source_surface["morphology"],
                int(source_surface["id"]),
            ),
        )
        return int(source_surface["id"])

    conn.execute(
        """
        UPDATE surface_forms
        SET pos_tag = COALESCE(pos_tag, ?),
            morphology = COALESCE(morphology, ?),
            seen_count = seen_count + ?,
            last_seen_at = CURRENT_TIMESTAMP,
            pronunciation_audio = COALESCE(pronunciation_audio, ?),
            pronunciation_mime_type = COALESCE(pronunciation_mime_type, ?),
            pronunciation_provider = COALESCE(pronunciation_provider, ?),
            pronunciation_model = COALESCE(pronunciation_model, ?),
            pronunciation_generated_at = COALESCE(pronunciation_generated_at, ?)
        WHERE id = ?
        """,
        (
            source_surface["pos_tag"],
            source_surface["morphology"],
            int(source_surface["seen_count"] or 0),
            source_surface["pronunciation_audio"],
            source_surface["pronunciation_mime_type"],
            source_surface["pronunciation_provider"],
            source_surface["pronunciation_model"],
            source_surface["pronunciation_generated_at"],
            int(existing["id"]),
        ),
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO surface_form_cor_variants (surface_form_id, cor_id)
        SELECT ?, cor_id
        FROM surface_form_cor_variants
        WHERE surface_form_id = ?
        """,
        (int(existing["id"]), int(source_surface["id"])),
    )
    conn.execute("DELETE FROM surface_forms WHERE id = ?", (int(source_surface["id"]),))
    return int(existing["id"])


def delete_meaning_if_empty(conn: sqlite3.Connection, *, meaning_id: int) -> None:
    surface_row = conn.execute(
        "SELECT 1 FROM surface_forms WHERE meaning_id = ? LIMIT 1",
        (meaning_id,),
    ).fetchone()
    if surface_row is not None:
        return
    conn.execute("DELETE FROM lexeme_meanings WHERE id = ?", (meaning_id,))


def delete_lexeme_if_empty(conn: sqlite3.Connection, *, lexeme_id: int) -> None:
    surface_row = conn.execute(
        "SELECT 1 FROM surface_forms WHERE lexeme_id = ? LIMIT 1",
        (lexeme_id,),
    ).fetchone()
    meaning_row = conn.execute(
        "SELECT 1 FROM lexeme_meanings WHERE lexeme_id = ? LIMIT 1",
        (lexeme_id,),
    ).fetchone()
    if surface_row is None and meaning_row is None:
        conn.execute("DELETE FROM lexemes WHERE id = ?", (lexeme_id,))


def select_surface(conn: sqlite3.Connection, *, lexeme_id: int, meaning_id: int | None, form: str):
    if meaning_id is None:
        return conn.execute(
            """
            SELECT *
            FROM surface_forms
            WHERE lexeme_id = ? AND meaning_id IS NULL AND form = ?
            LIMIT 1
            """,
            (lexeme_id, form),
        ).fetchone()
    return conn.execute(
        """
        SELECT *
        FROM surface_forms
        WHERE lexeme_id = ? AND meaning_id = ? AND form = ?
        LIMIT 1
        """,
        (lexeme_id, meaning_id, form),
    ).fetchone()


def build_before_snapshot(
    conn: sqlite3.Connection,
    *,
    source_lexeme,
    source_meaning,
    stored_surface_form: str | None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "lemma": dict(source_lexeme),
        "meaning": dict(source_meaning) if source_meaning is not None else None,
    }
    if stored_surface_form:
        if source_meaning is not None:
            surface = load_meaning_surface(conn, meaning_id=int(source_meaning["id"]), form=stored_surface_form)
        else:
            surface = select_surface(conn, lexeme_id=int(source_lexeme["id"]), meaning_id=None, form=stored_surface_form)
        payload["surface_form"] = dict(surface) if surface is not None else None
    return payload


def build_after_snapshot(
    conn: sqlite3.Connection,
    *,
    target_lexeme,
    target_meaning_id: int | None,
    stored_surface_form: str | None,
) -> dict[str, object]:
    if target_lexeme is None:
        return {}
    payload: dict[str, object] = {"lemma": dict(target_lexeme)}
    if target_meaning_id is not None:
        meaning = conn.execute(
            """
            SELECT id, lexeme_id, meaning_key, cor_lemma_idx, gloss, english_translation, pos_tag, morphology
            FROM lexeme_meanings
            WHERE id = ?
            LIMIT 1
            """,
            (target_meaning_id,),
        ).fetchone()
        payload["meaning"] = dict(meaning) if meaning is not None else None
    if stored_surface_form:
        payload["surface_form"] = dict(
            conn.execute(
                """
                SELECT *
                FROM surface_forms
                WHERE lexeme_id = ? AND form = ?
                ORDER BY CASE WHEN meaning_id = ? THEN 0 ELSE 1 END, id ASC
                LIMIT 1
                """,
                (int(target_lexeme["id"]), stored_surface_form, target_meaning_id),
            ).fetchone()
            or {}
        )
    return payload


def clean_str(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def required_str(value: object, field_name: str) -> str:
    cleaned = clean_str(value)
    if cleaned is None:
        raise ValueError(f"{field_name} is required")
    return cleaned


def required_int(value: object, field_name: str) -> int:
    if not isinstance(value, int):
        raise ValueError(f"{field_name} is required")
    return value


def normalize_target_lemma(value: str) -> str:
    normalized = normalize_token(value)
    if not normalized:
        raise ValueError("target_lemma is required")
    return normalized
