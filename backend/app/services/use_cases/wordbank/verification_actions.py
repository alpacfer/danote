from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.db.migrations import get_connection
from app.services.cor_local import CORLocalEntry
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.collaborators.cor import CorResolutionCollaborator
from app.services.use_cases.wordbank.noun_variations import (
    TARGET_NOUN_SLOTS,
    extract_fix_variations_action_slot_forms,
    noun_meaning_context_from_rows,
    noun_slot_from_morphology,
    resolve_target_noun_slot_entries,
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


@dataclass(frozen=True)
class VerificationActionExecutionResult:
    status: Literal["applied", "skipped"]
    applied_action_type: str | None
    target_lemma: str | None
    target_meaning_id: int | None
    log_payload: dict[str, object] | None
    invalidate_targets: tuple[tuple[str, str | None], ...]


@dataclass(frozen=True)
class DesiredNounVariationSlot:
    form: str
    pos_tag: str | None
    morphology: str | None
    cor_id: str | None = None


def apply_verification_action(
    *,
    db_path: Path,
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
        source_lexeme = fetch_lexeme_by_lemma(conn, normalized_lemma)
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
            )
        elif action_type == "fix_gloss":
            result = _apply_fix_gloss(
                conn,
                source_lexeme=source_lexeme,
                source_meaning=source_meaning,
                gloss=required_str(action.get("gloss"), "gloss"),
                stored_surface_form=normalized_surface,
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
        after_lexeme = fetch_lexeme_by_lemma(conn, after_lemma)
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


def _apply_fix_gloss(
    conn: sqlite3.Connection,
    *,
    source_lexeme,
    source_meaning,
    gloss: str,
    stored_surface_form: str | None,
) -> VerificationActionExecutionResult:
    if source_meaning is None:
        raise ValueError("fix_gloss requires a meaning-scoped entry.")
    conn.execute(
        """
        UPDATE lexeme_meanings
        SET gloss = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (gloss, int(source_meaning["id"])),
    )
    lemma = str(source_lexeme["lemma"])
    meaning_id = int(source_meaning["id"])
    return VerificationActionExecutionResult(
        status="applied",
        applied_action_type="fix_gloss",
        target_lemma=lemma,
        target_meaning_id=meaning_id,
        log_payload={
            "action_type": "fix_gloss",
            "source": {"lemma": lemma, "meaning_id": meaning_id, "surface_form": stored_surface_form},
            "target": {"lemma": lemma, "meaning_id": meaning_id},
            "action": {"gloss": gloss},
        },
        invalidate_targets=((lemma, stored_surface_form),),
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


def _apply_fix_variations(
    conn: sqlite3.Connection,
    *,
    cor: CorResolutionCollaborator,
    source_lexeme,
    source_meaning,
    action: dict[str, object],
) -> VerificationActionExecutionResult:
    context = noun_meaning_context_from_rows(
        source_lexeme=source_lexeme,
        source_meaning=source_meaning,
    )
    fallback_slot_entries = resolve_target_noun_slot_entries(
        cor,
        context=context,
        allow_lemma_mismatch=True,
    )
    desired_slots = _resolve_fix_variations_slots(
        action=action,
        fallback_slot_entries=fallback_slot_entries,
    )
    if not desired_slots:
        raise RuntimeError("No COR-backed noun variations were found for this meaning.")

    current_rows = conn.execute(
        """
        SELECT *
        FROM surface_forms
        WHERE meaning_id = ?
        ORDER BY id ASC
        """,
        (context.meaning_id,),
    ).fetchall()
    rows_by_slot: dict[str, list[sqlite3.Row]] = {}
    for row in current_rows:
        normalized_form = normalize_token(str(row["form"]))
        if not normalized_form or normalized_form == context.lemma:
            continue
        slot = noun_slot_from_morphology(row["morphology"])
        if slot is None:
            continue
        rows_by_slot.setdefault(slot, []).append(row)

    changed_forms: list[str] = []
    mutated = False
    for slot_name, _number, _definite in TARGET_NOUN_SLOTS:
        desired_slot = desired_slots.get(slot_name)
        if desired_slot is None:
            continue
        desired_form = normalize_token(desired_slot.form)
        if not desired_form:
            continue
        slot_rows = rows_by_slot.get(slot_name, [])
        matching_row = next(
            (row for row in slot_rows if normalize_token(str(row["form"])) == desired_form),
            None,
        )
        if matching_row is None and slot_rows:
            matching_row = slot_rows[0]

        if matching_row is None:
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
                (
                    context.lexeme_id,
                    context.meaning_id,
                    desired_slot.form,
                    "search",
                    1,
                    desired_slot.pos_tag,
                    desired_slot.morphology,
                ),
            )
            surface_row = conn.execute(
                """
                SELECT *
                FROM surface_forms
                WHERE lexeme_id = ? AND meaning_id = ? AND form = ?
                LIMIT 1
                """,
                (context.lexeme_id, context.meaning_id, desired_slot.form),
            ).fetchone()
            if surface_row is None:
                raise RuntimeError("Failed to insert corrected noun variation.")
            matching_row = surface_row
            mutated = True
            changed_forms.append(desired_slot.form)
        else:
            current_form = normalize_token(str(matching_row["form"]))
            current_cor_id = _current_surface_form_cor_id(conn, surface_form_id=int(matching_row["id"]))
            needs_row_update = (
                current_form != desired_form
                or str(matching_row["source"]) != "search"
                or (matching_row["pos_tag"] or None) != desired_slot.pos_tag
                or (matching_row["morphology"] or None) != desired_slot.morphology
                or matching_row["pronunciation_audio"] is not None
                or matching_row["pronunciation_mime_type"] is not None
                or matching_row["pronunciation_provider"] is not None
                or matching_row["pronunciation_model"] is not None
                or matching_row["pronunciation_generated_at"] is not None
            )
            if needs_row_update:
                mutated = True
                if current_form != desired_form:
                    changed_forms.append(desired_slot.form)
                conn.execute(
                    """
                    UPDATE surface_forms
                    SET form = ?,
                        source = ?,
                        pos_tag = ?,
                        morphology = ?,
                        pronunciation_audio = NULL,
                        pronunciation_mime_type = NULL,
                        pronunciation_provider = NULL,
                        pronunciation_model = NULL,
                        pronunciation_generated_at = NULL,
                        last_seen_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (
                        desired_slot.form,
                        "search",
                        desired_slot.pos_tag,
                        desired_slot.morphology,
                        int(matching_row["id"]),
                    ),
                )
            if current_cor_id != desired_slot.cor_id:
                mutated = True
                conn.execute(
                    "DELETE FROM surface_form_cor_variants WHERE surface_form_id = ?",
                    (int(matching_row["id"]),),
                )
                if desired_slot.cor_id:
                    conn.execute(
                        """
                        INSERT INTO surface_form_cor_variants (surface_form_id, cor_id)
                        VALUES (?, ?)
                        """,
                        (int(matching_row["id"]), desired_slot.cor_id),
                    )

        if matching_row is not None and _current_surface_form_cor_id(conn, surface_form_id=int(matching_row["id"])) is None and desired_slot.cor_id:
            conn.execute(
                """
                INSERT INTO surface_form_cor_variants (surface_form_id, cor_id)
                VALUES (?, ?)
                """,
                (int(matching_row["id"]), desired_slot.cor_id),
            )
            mutated = True

        preserved_row_id = int(matching_row["id"])
        for row in slot_rows:
            if int(row["id"]) == preserved_row_id:
                continue
            conn.execute("DELETE FROM surface_forms WHERE id = ?", (int(row["id"]),))
            mutated = True

    lemma = str(source_lexeme["lemma"])
    meaning_id = int(source_meaning["id"])
    if not mutated:
        return VerificationActionExecutionResult(
            status="skipped",
            applied_action_type=None,
            target_lemma=lemma,
            target_meaning_id=meaning_id,
            log_payload=None,
            invalidate_targets=((lemma, None),),
        )
    changed_forms = sorted({normalize_token(form) or form for form in changed_forms})
    return VerificationActionExecutionResult(
        status="applied",
        applied_action_type="fix_variations",
        target_lemma=lemma,
        target_meaning_id=meaning_id,
        log_payload={
            "action_type": "fix_variations",
            "source": {"lemma": lemma, "meaning_id": meaning_id, "surface_form": None},
            "target": {"lemma": lemma, "meaning_id": meaning_id},
            "action": {"updated_surface_forms": changed_forms},
        },
        invalidate_targets=tuple((lemma, form) for form in changed_forms) or ((lemma, None),),
    )


def _resolve_fix_variations_slots(
    *,
    action: dict[str, object],
    fallback_slot_entries: dict[str, CORLocalEntry],
) -> dict[str, DesiredNounVariationSlot]:
    action_slot_forms = extract_fix_variations_action_slot_forms(action)
    if not action_slot_forms:
        return {
            slot_name: DesiredNounVariationSlot(
                form=entry.form,
                pos_tag=entry.pos_tag,
                morphology=entry.morphology,
                cor_id=entry.cor_id,
            )
            for slot_name, entry in fallback_slot_entries.items()
        }

    desired_slots: dict[str, DesiredNounVariationSlot] = {}
    for slot_name, _number, _definite in TARGET_NOUN_SLOTS:
        fallback_entry = fallback_slot_entries.get(slot_name)
        desired_form = action_slot_forms.get(slot_name)
        if desired_form is None and fallback_entry is None:
            continue
        if desired_form is None and fallback_entry is not None:
            desired_slots[slot_name] = DesiredNounVariationSlot(
                form=fallback_entry.form,
                pos_tag=fallback_entry.pos_tag,
                morphology=fallback_entry.morphology,
                cor_id=fallback_entry.cor_id,
            )
            continue
        desired_slots[slot_name] = DesiredNounVariationSlot(
            form=desired_form,
            pos_tag=fallback_entry.pos_tag if fallback_entry is not None else "NOUN",
            morphology=fallback_entry.morphology if fallback_entry is not None else None,
            cor_id=(
                fallback_entry.cor_id
                if fallback_entry is not None and normalize_token(fallback_entry.form) == normalize_token(desired_form)
                else None
            ),
        )
    return desired_slots


def _current_surface_form_cor_id(conn: sqlite3.Connection, *, surface_form_id: int) -> str | None:
    row = conn.execute(
        """
        SELECT cor_id
        FROM surface_form_cor_variants
        WHERE surface_form_id = ?
        ORDER BY id ASC
        LIMIT 1
        """,
        (surface_form_id,),
    ).fetchone()
    return str(row["cor_id"]) if row is not None and row["cor_id"] else None
