from __future__ import annotations

import sqlite3
from pathlib import Path

from app.db.migrations import get_connection
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.collaborators.cor import CorResolutionCollaborator
from app.services.use_cases.wordbank.verification_action_models import (
    VerificationActionExecutionResult,
)
from app.services.use_cases.wordbank.verification_action_support import (
    build_after_snapshot,
    build_before_snapshot,
    clean_str,
    delete_lexeme_if_empty,
    delete_meaning_if_empty,
    ensure_surface_exists,
    ensure_target_lexeme,
    ensure_target_meaning,
    fetch_lexeme_by_lemma,
    load_meaning_surface,
    load_requested_meaning,
    move_or_merge_surface_form,
    required_int,
    required_str,
)
from app.services.use_cases.wordbank.verification_fix_variations import (
    apply_fix_variations as _apply_fix_variations,
)


def apply_verification_action(
    *,
    db_path: Path,
    owner_user_id: int = 1,
    cor: CorResolutionCollaborator,
    stored_lemma: str,
    stored_surface_form: str | None,
    meaning_id: int | None,
    action: dict[str, object],
    provider_name: str,
) -> VerificationActionExecutionResult:
    normalized_lemma = normalize_token(stored_lemma)
    normalized_surface = normalize_token(stored_surface_form or "") or None
    action_type = clean_str(action.get("action_type"))
    if not normalized_lemma:
        raise ValueError("stored_lemma is required")
    if action_type is None:
        return VerificationActionExecutionResult(
            status="skipped",
            applied_action_type=None,
            target_lemma=normalized_lemma,
            target_meaning_id=meaning_id,
            log_payload=None,
            invalidate_targets=((normalized_lemma, normalized_surface),),
        )

    with get_connection(db_path) as conn:
        source_lexeme = fetch_lexeme_by_lemma(
            conn,
            normalized_lemma,
            owner_user_id=owner_user_id,
        )
        if source_lexeme is None:
            raise LookupError(f"Lemma '{normalized_lemma}' was not found")
        source_meaning = load_requested_meaning(
            conn,
            lexeme_id=int(source_lexeme["id"]),
            meaning_id=meaning_id,
            normalized_lemma=normalized_lemma,
        )
        before_payload = build_before_snapshot(
            conn,
            source_lexeme=source_lexeme,
            source_meaning=source_meaning,
            stored_surface_form=normalized_surface,
        )

        if action_type == "fix_translation":
            result = _apply_fix_translation(
                conn,
                source_lexeme=source_lexeme,
                source_meaning=source_meaning,
                english_translation=required_str(action.get("english_translation"), "english_translation"),
                provider_name=provider_name,
                stored_surface_form=normalized_surface,
                owner_user_id=owner_user_id,
            )
        elif action_type == "fix_variations":
            result = _apply_fix_variations(
                conn,
                cor=cor,
                source_lexeme=source_lexeme,
                source_meaning=source_meaning,
                action=action,
            )
        elif action_type == "move_to_meaning_section":
            result = _apply_move_to_meaning_section(
                conn,
                source_lexeme=source_lexeme,
                source_meaning=source_meaning,
                stored_surface_form=normalized_surface,
                target_meaning_id=required_int(action.get("target_meaning_id"), "target_meaning_id"),
            )
        elif action_type == "move_to_lemma":
            result = _apply_move_to_lemma(
                conn,
                source_lexeme=source_lexeme,
                source_meaning=source_meaning,
                stored_surface_form=normalized_surface,
                target_lemma=required_str(action.get("target_lemma"), "target_lemma"),
                target_meaning_key=required_str(action.get("target_meaning_key"), "target_meaning_key"),
                target_gloss=clean_str(action.get("target_gloss")),
                target_english_translation=clean_str(action.get("target_english_translation")),
                target_pos_tag=clean_str(action.get("target_pos_tag")),
                target_morphology=clean_str(action.get("target_morphology")),
                provider_name=provider_name,
                owner_user_id=owner_user_id,
            )
        else:
            result = VerificationActionExecutionResult(
                status="skipped",
                applied_action_type=None,
                target_lemma=normalized_lemma,
                target_meaning_id=meaning_id,
                log_payload=None,
                invalidate_targets=((normalized_lemma, normalized_surface),),
            )

        if result.log_payload is None:
            return result

        after_lemma = result.target_lemma or normalized_lemma
        after_meaning = result.target_meaning_id
        after_lexeme = fetch_lexeme_by_lemma(
            conn,
            after_lemma,
            owner_user_id=owner_user_id,
        )
        after_payload = build_after_snapshot(
            conn,
            target_lexeme=after_lexeme,
            target_meaning_id=after_meaning,
            stored_surface_form=normalized_surface,
        )
        log_payload = {
            **result.log_payload,
            "before": before_payload,
            "after": after_payload,
        }
        return VerificationActionExecutionResult(
            status=result.status,
            applied_action_type=result.applied_action_type,
            target_lemma=result.target_lemma,
            target_meaning_id=result.target_meaning_id,
            log_payload=log_payload,
            invalidate_targets=result.invalidate_targets,
        )


def _apply_fix_translation(
    conn: sqlite3.Connection,
    *,
    source_lexeme,
    source_meaning,
    english_translation: str,
    provider_name: str,
    stored_surface_form: str | None,
    owner_user_id: int,
) -> VerificationActionExecutionResult:
    if source_meaning is not None:
        conn.execute(
            """
            UPDATE lexeme_meanings
            SET english_translation = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (english_translation, int(source_meaning["id"])),
        )
        target_meaning_id = int(source_meaning["id"])
        _propagate_fix_translation_to_sentence_tokens(
            conn,
            english_translation=english_translation,
            meaning_id=target_meaning_id,
            lexeme_id=None,
            owner_user_id=owner_user_id,
        )
    else:
        conn.execute(
            """
            UPDATE lexemes
            SET english_translation = ?, translation_provider = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (english_translation, provider_name, int(source_lexeme["id"])),
        )
        target_meaning_id = None
        _propagate_fix_translation_to_sentence_tokens(
            conn,
            english_translation=english_translation,
            meaning_id=None,
            lexeme_id=int(source_lexeme["id"]),
            owner_user_id=owner_user_id,
        )
    lemma = str(source_lexeme["lemma"])
    return VerificationActionExecutionResult(
        status="applied",
        applied_action_type="fix_translation",
        target_lemma=lemma,
        target_meaning_id=target_meaning_id,
        log_payload={
            "action_type": "fix_translation",
            "source": {"lemma": lemma, "meaning_id": target_meaning_id, "surface_form": stored_surface_form},
            "target": {"lemma": lemma, "meaning_id": target_meaning_id},
            "action": {"english_translation": english_translation},
        },
        invalidate_targets=((lemma, stored_surface_form),),
    )


def _propagate_fix_translation_to_sentence_tokens(
    conn: sqlite3.Connection,
    *,
    english_translation: str,
    meaning_id: int | None,
    lexeme_id: int | None,
    owner_user_id: int,
) -> None:
    """Refresh denormalized english_translation on saved sentence tokens.

    sentence_bank_tokens stores english_translation per token. When a meaning- or
    lemma-scoped fix_translation lands, every saved token that references that scope
    must reflect the new translation so sentence pages and the sentence search
    preview don't show the stale value.
    """
    if meaning_id is not None:
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
            (english_translation, meaning_id, owner_user_id),
        )
        return
    if lexeme_id is not None:
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
            (english_translation, lexeme_id, owner_user_id),
        )


def _apply_move_to_meaning_section(
    conn: sqlite3.Connection,
    *,
    source_lexeme,
    source_meaning,
    stored_surface_form: str | None,
    target_meaning_id: int,
) -> VerificationActionExecutionResult:
    if source_meaning is None:
        raise ValueError("move_to_meaning_section requires a meaning-scoped entry.")
    if not stored_surface_form:
        raise ValueError("move_to_meaning_section requires stored_surface_form.")

    lemma = str(source_lexeme["lemma"])
    target_meaning = conn.execute(
        """
        SELECT id, lexeme_id, meaning_key, gloss, english_translation, pos_tag, morphology
        FROM lexeme_meanings
        WHERE id = ? AND lexeme_id = ?
        LIMIT 1
        """,
        (target_meaning_id, int(source_lexeme["id"])),
    ).fetchone()
    if target_meaning is None:
        raise LookupError(f"Meaning '{target_meaning_id}' was not found for '{lemma}'")

    source_surface = load_meaning_surface(conn, meaning_id=int(source_meaning["id"]), form=stored_surface_form)
    if source_surface is None:
        raise LookupError(f"Surface form '{stored_surface_form}' was not found in meaning '{int(source_meaning['id'])}'")

    move_or_merge_surface_form(
        conn,
        source_surface=source_surface,
        target_lexeme_id=int(source_lexeme["id"]),
        target_meaning_id=int(target_meaning["id"]),
        new_form=stored_surface_form,
    )
    delete_meaning_if_empty(conn, meaning_id=int(source_meaning["id"]))
    return VerificationActionExecutionResult(
        status="applied",
        applied_action_type="move_to_meaning_section",
        target_lemma=lemma,
        target_meaning_id=int(target_meaning["id"]),
        log_payload={
            "action_type": "move_to_meaning_section",
            "source": {"lemma": lemma, "meaning_id": int(source_meaning["id"]), "surface_form": stored_surface_form},
            "target": {"lemma": lemma, "meaning_id": int(target_meaning["id"])},
            "action": {"target_meaning_id": int(target_meaning["id"])},
        },
        invalidate_targets=((lemma, stored_surface_form),),
    )


def _apply_move_to_lemma(
    conn: sqlite3.Connection,
    *,
    source_lexeme,
    source_meaning,
    stored_surface_form: str | None,
    target_lemma: str,
    target_meaning_key: str,
    target_gloss: str | None,
    target_english_translation: str | None,
    target_pos_tag: str | None,
    target_morphology: str | None,
    provider_name: str,
    owner_user_id: int,
) -> VerificationActionExecutionResult:
    normalized_target_lemma = normalize_token(target_lemma)
    if not normalized_target_lemma:
        raise ValueError("target_lemma is required")

    source_lemma = str(source_lexeme["lemma"])
    target_lexeme = ensure_target_lexeme(
        conn,
        lemma=normalized_target_lemma,
        english_translation=target_english_translation,
        provider_name=provider_name,
        pos_tag=target_pos_tag or (source_meaning["pos_tag"] if source_meaning is not None else source_lexeme["pos_tag"]),
        morphology=target_morphology or (source_meaning["morphology"] if source_meaning is not None else source_lexeme["morphology"]),
        owner_user_id=owner_user_id,
    )

    if source_meaning is not None:
        target_meaning = ensure_target_meaning(
            conn,
            lexeme_id=int(target_lexeme["id"]),
            meaning_key=normalize_token(target_meaning_key) or normalized_target_lemma,
            gloss=target_gloss,
            english_translation=target_english_translation or source_meaning["english_translation"],
            pos_tag=target_pos_tag or source_meaning["pos_tag"],
            morphology=target_morphology or source_meaning["morphology"],
            cor_lemma_idx=None,
        )
        source_surfaces = conn.execute(
            """
            SELECT *
            FROM surface_forms
            WHERE meaning_id = ?
            ORDER BY id ASC
            """,
            (int(source_meaning["id"]),),
        ).fetchall()
        for row in source_surfaces:
            new_form = normalized_target_lemma if normalize_token(row["form"]) == source_lemma else str(row["form"])
            move_or_merge_surface_form(
                conn,
                source_surface=row,
                target_lexeme_id=int(target_lexeme["id"]),
                target_meaning_id=int(target_meaning["id"]),
                new_form=new_form,
            )
        ensure_surface_exists(
            conn,
            lexeme_id=int(target_lexeme["id"]),
            meaning_id=int(target_meaning["id"]),
            form=normalized_target_lemma,
            pos_tag=target_pos_tag or source_meaning["pos_tag"],
            morphology=target_morphology or source_meaning["morphology"],
        )
        delete_meaning_if_empty(conn, meaning_id=int(source_meaning["id"]))
        target_meaning_id = int(target_meaning["id"])
    else:
        source_surfaces = conn.execute(
            """
            SELECT *
            FROM surface_forms
            WHERE lexeme_id = ? AND meaning_id IS NULL
            ORDER BY id ASC
            """,
            (int(source_lexeme["id"]),),
        ).fetchall()
        for row in source_surfaces:
            new_form = normalized_target_lemma if normalize_token(row["form"]) == source_lemma else str(row["form"])
            move_or_merge_surface_form(
                conn,
                source_surface=row,
                target_lexeme_id=int(target_lexeme["id"]),
                target_meaning_id=None,
                new_form=new_form,
            )
        ensure_surface_exists(
            conn,
            lexeme_id=int(target_lexeme["id"]),
            meaning_id=None,
            form=normalized_target_lemma,
            pos_tag=target_pos_tag or source_lexeme["pos_tag"],
            morphology=target_morphology or source_lexeme["morphology"],
        )
        target_meaning_id = None

    delete_lexeme_if_empty(conn, lexeme_id=int(source_lexeme["id"]))
    invalidate_targets = (
        (source_lemma, stored_surface_form),
        (normalized_target_lemma, stored_surface_form if stored_surface_form != source_lemma else normalized_target_lemma),
    )
    return VerificationActionExecutionResult(
        status="applied",
        applied_action_type="move_to_lemma",
        target_lemma=normalized_target_lemma,
        target_meaning_id=target_meaning_id,
        log_payload={
            "action_type": "move_to_lemma",
            "source": {"lemma": source_lemma, "meaning_id": int(source_meaning["id"]) if source_meaning is not None else None, "surface_form": stored_surface_form},
            "target": {"lemma": normalized_target_lemma, "meaning_id": target_meaning_id},
            "action": {
                "target_lemma": normalized_target_lemma,
                "target_meaning_key": normalize_token(target_meaning_key) or normalized_target_lemma,
                "target_gloss": target_gloss,
                "target_english_translation": target_english_translation,
                "target_pos_tag": target_pos_tag,
                "target_morphology": target_morphology,
            },
        },
        invalidate_targets=invalidate_targets,
    )
