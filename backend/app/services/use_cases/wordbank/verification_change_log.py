from __future__ import annotations

import logging
from pathlib import Path

from app.db.repositories.wordbank import WordbankRepository
from app.db.sqlite import get_connection

logger = logging.getLogger(__name__)


def query_surface_forms_snapshot(
    db_path: Path,
    *,
    lexeme_id: int,
    meaning_id: int | None,
) -> list[dict[str, object]]:
    """Return all surface forms for a (lexeme_id, meaning_id) scope before a change."""
    with get_connection(db_path) as conn:
        if meaning_id is None:
            rows = conn.execute(
                """
                SELECT form, pos_tag, morphology, source, meaning_id
                FROM surface_forms
                WHERE lexeme_id = ? AND meaning_id IS NULL
                ORDER BY id ASC
                """,
                (lexeme_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT form, pos_tag, morphology, source, meaning_id
                FROM surface_forms
                WHERE lexeme_id = ? AND meaning_id = ?
                ORDER BY id ASC
                """,
                (lexeme_id, meaning_id),
            ).fetchall()
        return [dict(row) for row in rows]


def build_change_log_before_json(
    *,
    action_type: str,
    meaning_id: int | None,
    before_snapshot: dict[str, object],
    pre_apply_surfaces: list[dict[str, object]] | None,
) -> dict[str, object]:
    """Build a minimal, revertable before-state dict for the change log."""
    if action_type == "fix_translation":
        meaning = before_snapshot.get("meaning")
        lemma_row = before_snapshot.get("lemma") or {}
        if meaning is not None and isinstance(meaning, dict):
            old_translation = meaning.get("english_translation")
        else:
            old_translation = lemma_row.get("english_translation") if isinstance(lemma_row, dict) else None
        return {
            "action_type": "fix_translation",
            "meaning_id": meaning_id,
            "english_translation": old_translation,
        }
    if action_type == "fix_variations":
        return {
            "action_type": "fix_variations",
            "meaning_id": meaning_id,
            "surface_forms": pre_apply_surfaces or [],
        }
    return {"action_type": action_type, "meaning_id": meaning_id}


def revert_fix_translation(
    *,
    db_path: Path,
    owner_user_id: int = 1,
    stored_lemma: str,
    meaning_id: int | None,
    old_translation: str | None,
) -> None:
    """Restore the english_translation to its pre-apply value."""
    repository = WordbankRepository(db_path, owner_user_id=owner_user_id)
    lexeme = repository.get_lexeme(stored_lemma)
    if lexeme is None:
        raise LookupError(f"Lemma '{stored_lemma}' not found")
    with get_connection(db_path) as conn:
        if meaning_id is not None:
            conn.execute(
                "UPDATE lexeme_meanings SET english_translation = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (old_translation, meaning_id),
            )
            conn.execute(
                """
                UPDATE sentence_bank_tokens
                SET english_translation = ?
                WHERE meaning_id = ?
                  AND save_status = 'saved'
                  AND EXISTS (
                    SELECT 1
                    FROM sentence_bank sb
                    WHERE sb.id = sentence_bank_tokens.sentence_id
                      AND sb.owner_user_id = ?
                  )
                """,
                (old_translation, meaning_id, owner_user_id),
            )
        else:
            conn.execute(
                "UPDATE lexemes SET english_translation = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (old_translation, lexeme.id),
            )
            conn.execute(
                """
                UPDATE sentence_bank_tokens
                SET english_translation = ?
                WHERE lexeme_id = ?
                  AND meaning_id IS NULL
                  AND save_status = 'saved'
                  AND EXISTS (
                    SELECT 1
                    FROM sentence_bank sb
                    WHERE sb.id = sentence_bank_tokens.sentence_id
                      AND sb.owner_user_id = ?
                  )
                """,
                (old_translation, lexeme.id, owner_user_id),
            )


def revert_fix_variations(
    *,
    db_path: Path,
    owner_user_id: int = 1,
    stored_lemma: str,
    meaning_id: int | None,
    surface_forms_snapshot: list[dict[str, object]],
) -> None:
    """Restore surface forms to their pre-apply snapshot."""
    repository = WordbankRepository(db_path, owner_user_id=owner_user_id)
    lexeme = repository.get_lexeme(stored_lemma)
    if lexeme is None:
        raise LookupError(f"Lemma '{stored_lemma}' not found")
    with get_connection(db_path) as conn:
        # Delete current surface forms for this scope
        if meaning_id is None:
            conn.execute(
                "DELETE FROM surface_forms WHERE lexeme_id = ? AND meaning_id IS NULL",
                (lexeme.id,),
            )
        else:
            conn.execute(
                "DELETE FROM surface_forms WHERE lexeme_id = ? AND meaning_id = ?",
                (lexeme.id, meaning_id),
            )
        # Re-insert snapshot forms
        for form in surface_forms_snapshot:
            conn.execute(
                """
                INSERT OR IGNORE INTO surface_forms (lexeme_id, form, source, pos_tag, morphology, meaning_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    lexeme.id,
                    form["form"],
                    form.get("source") or "manual",
                    form.get("pos_tag"),
                    form.get("morphology"),
                    meaning_id,
                ),
            )
