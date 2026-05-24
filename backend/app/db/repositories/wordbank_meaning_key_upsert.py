from __future__ import annotations

from pathlib import Path

from app.db.repositories.wordbank_models import LexemeMeaningRecord, lexeme_meaning_from_row
from app.db.sqlite import get_connection, timed_db_operation


def upsert_lexeme_meaning_by_key(
    *,
    db_path: Path,
    owner_user_id: int,
    lexeme_id: int,
    meaning_key: str,
    cor_lemma_idx: int | None,
    dictionary_status: str,
    gloss: str | None,
    english_translation: str | None,
    pos_tag: str | None,
    morphology: str | None,
    english_gloss: str | None = None,
) -> tuple[LexemeMeaningRecord, bool]:
    """Insert/update a meaning row keyed strictly on ``(lexeme_id, meaning_key)``.

    ``WordbankRepository.upsert_lexeme_meaning`` dedupes on ``cor_lemma_idx``
    first, which is correct for single-meaning POS (nouns/adjectives where each
    COR lemma_idx maps to one sense). For the sense-discovery fan-out path,
    many senses of a verb share one COR lemma_idx, so we must dedupe by
    ``meaning_key`` instead — otherwise saving a second sense silently rewrites
    the first sense's row. ``cor_lemma_idx`` is still recorded on the row so
    downstream lookups (gram_raw, gloss_translation, COR joins) keep working.
    """
    with timed_db_operation("wordbank.upsert_lexeme_meaning_by_key"), get_connection(db_path) as conn:
        if conn.execute(
            "SELECT 1 FROM lexemes WHERE id = ? AND owner_user_id = ? LIMIT 1",
            (lexeme_id, owner_user_id),
        ).fetchone() is None:
            raise LookupError("lexeme was not found")
        row = conn.execute(
            """
            SELECT id, meaning_key, cor_lemma_idx, dictionary_status, gloss,
                   english_translation, pos_tag, morphology, lexeme_id, english_gloss
            FROM lexeme_meanings
            WHERE lexeme_id = ? AND meaning_key = ?
              AND EXISTS (
                SELECT 1 FROM lexemes l
                WHERE l.id = lexeme_meanings.lexeme_id AND l.owner_user_id = ?
              )
            LIMIT 1
            """,
            (lexeme_id, meaning_key, owner_user_id),
        ).fetchone()
        inserted = False
        if row is None:
            cursor = conn.execute(
                """
                INSERT INTO lexeme_meanings (
                    lexeme_id, meaning_key, cor_lemma_idx, dictionary_status,
                    gloss, english_translation, pos_tag, morphology, english_gloss
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (lexeme_id, meaning_key, cor_lemma_idx, dictionary_status,
                 gloss, english_translation, pos_tag, morphology, english_gloss),
            )
            inserted = True
            row_id = cursor.lastrowid
        else:
            conn.execute(
                """
                UPDATE lexeme_meanings
                SET cor_lemma_idx = COALESCE(cor_lemma_idx, ?),
                    dictionary_status = CASE
                        WHEN dictionary_status = 'cor' OR ? = 'cor' THEN 'cor'
                        WHEN dictionary_status = 'generated_non_cor' OR ? = 'generated_non_cor' THEN 'generated_non_cor'
                        ELSE 'unknown'
                    END,
                    gloss = COALESCE(gloss, ?),
                    english_translation = COALESCE(english_translation, ?),
                    english_gloss = COALESCE(english_gloss, ?),
                    pos_tag = COALESCE(pos_tag, ?),
                    morphology = COALESCE(morphology, ?),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (cor_lemma_idx, dictionary_status, dictionary_status,
                 gloss, english_translation, english_gloss, pos_tag, morphology, int(row["id"])),
            )
            row_id = int(row["id"])
        row = conn.execute(
            "SELECT id, meaning_key, cor_lemma_idx, dictionary_status, gloss, english_translation, pos_tag, morphology, lexeme_id, english_gloss FROM lexeme_meanings WHERE id = ? LIMIT 1",
            (row_id,),
        ).fetchone()
    if row is None:
        raise RuntimeError("Failed to create or load lexeme meaning")
    return lexeme_meaning_from_row(row), inserted
