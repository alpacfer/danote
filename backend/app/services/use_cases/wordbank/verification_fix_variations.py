from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from app.services.cor_local import CORLocalEntry
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.collaborators.cor import CorResolutionCollaborator
from app.services.use_cases.wordbank.paradigm_variations import (
    ADJECTIVE_DISPLAY_SLOT_ORDER,
    ALL_NOUN_SLOTS,
    VERB_DISPLAY_SLOT_ORDER,
    action_slot_labels_for_kind,
    extract_fix_variations_action_slot_form_lists,
    extract_fix_variations_action_slot_forms,
    meaning_context_from_rows,
    noun_slot_from_morphology,
    paradigm_kind_from_pos_tag,
    resolve_target_slot_entries,
    slots_for_gram_raw_and_morphology,
    slots_for_entry,
)
from app.services.use_cases.wordbank.verification_action_models import VerificationActionExecutionResult


@dataclass(frozen=True)
class DesiredParadigmVariationForm:
    form: str
    pos_tag: str | None
    morphology: str | None
    cor_ids: tuple[str, ...] = ()


def apply_fix_variations(
    conn: sqlite3.Connection,
    *,
    cor: CorResolutionCollaborator,
    source_lexeme,
    source_meaning,
    action: dict[str, object],
) -> VerificationActionExecutionResult:
    context = meaning_context_from_rows(
        source_lexeme=source_lexeme,
        source_meaning=source_meaning,
    )
    fallback_slot_entries = resolve_target_slot_entries(
        cor,
        context=context,
        allow_lemma_mismatch=True,
    )
    desired_slots = _resolve_fix_variations_slots(
        paradigm_kind=context.paradigm_kind,
        action=action,
        fallback_slot_entries=fallback_slot_entries,
        lemma=context.lemma,
    )
    if not desired_slots:
        raise ValueError("fix_variations requires structured slot forms.")
    if context.paradigm_kind in {"adjective", "verb"}:
        return _apply_fix_variations_compacted(
            conn,
            cor=cor,
            context=context,
            desired_slots=desired_slots,
            source_lexeme=source_lexeme,
            source_meaning=source_meaning,
        )
    return _apply_fix_variations_noun(
        conn,
        context=context,
        desired_slots=desired_slots,
        source_lexeme=source_lexeme,
        source_meaning=source_meaning,
    )


def _apply_fix_variations_noun(
    conn: sqlite3.Connection,
    *,
    context,
    desired_slots: dict[str, tuple[DesiredParadigmVariationForm, ...]],
    source_lexeme,
    source_meaning,
) -> VerificationActionExecutionResult:
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
        if not normalized_form:
            continue
        slot = noun_slot_from_morphology(row["morphology"])
        if slot is None:
            continue
        rows_by_slot.setdefault(slot, []).append(row)

    affected_forms: list[str] = []
    mutated = False
    for slot_name, _number, _definite in ALL_NOUN_SLOTS:
        desired_forms = desired_slots.get(slot_name)
        if desired_forms is None:
            continue
        slot_rows = rows_by_slot.get(slot_name, [])
        current_signature = [
            (
                normalize_token(str(row["form"])) or str(row["form"]),
                str(row["source"]),
                row["pos_tag"] or None,
                row["morphology"] or None,
                _current_surface_form_cor_ids(conn, surface_form_id=int(row["id"])),
                row["pronunciation_audio"] is not None,
                row["pronunciation_mime_type"] is not None,
                row["pronunciation_provider"] is not None,
                row["pronunciation_model"] is not None,
                row["pronunciation_generated_at"] is not None,
            )
            for row in slot_rows
        ]
        desired_signature = [
            (
                normalize_token(form.form) or form.form,
                "search",
                form.pos_tag,
                form.morphology,
                form.cor_ids,
                False,
                False,
                False,
                False,
                False,
            )
            for form in desired_forms
        ]
        if current_signature == desired_signature:
            continue

        mutated = True
        affected_forms.extend(str(row["form"]) for row in slot_rows)
        affected_forms.extend(form.form for form in desired_forms)
        for row in slot_rows:
            conn.execute("DELETE FROM surface_form_cor_variants WHERE surface_form_id = ?", (int(row["id"]),))
            conn.execute("DELETE FROM surface_forms WHERE id = ?", (int(row["id"]),))
        for desired_form in desired_forms:
            surface_form_id = _insert_surface_form_row(
                conn,
                lexeme_id=context.lexeme_id,
                meaning_id=context.meaning_id,
                form=desired_form.form,
                pos_tag=desired_form.pos_tag,
                morphology=desired_form.morphology,
            )
            _insert_surface_form_cor_ids(conn, surface_form_id=surface_form_id, cor_ids=desired_form.cor_ids)

    return _fix_variations_result(
        mutated=mutated,
        affected_forms=affected_forms,
        source_lexeme=source_lexeme,
        source_meaning=source_meaning,
    )


def _apply_fix_variations_compacted(
    conn: sqlite3.Connection,
    *,
    cor: CorResolutionCollaborator,
    context,
    desired_slots: dict[str, tuple[DesiredParadigmVariationForm, ...]],
    source_lexeme,
    source_meaning,
) -> VerificationActionExecutionResult:
    current_rows = conn.execute(
        """
        SELECT *
        FROM surface_forms
        WHERE meaning_id = ?
        ORDER BY id ASC
        """,
        (context.meaning_id,),
    ).fetchall()
    managed_rows = [
        row
        for row in current_rows
        if any(
            slot in _managed_compacted_slots(context.paradigm_kind)
            for slot in _current_row_slots(
                cor,
                context=context,
                form=str(row["form"]),
                pos_tag=row["pos_tag"] or None,
                morphology=row["morphology"] or None,
            )
        )
    ]

    current_signature = sorted(
        (
            normalize_token(str(row["form"])) or str(row["form"]),
            str(row["source"]),
            row["pos_tag"] or None,
            row["morphology"] or None,
            _current_surface_form_cor_ids(conn, surface_form_id=int(row["id"])),
            row["pronunciation_audio"] is not None,
            row["pronunciation_mime_type"] is not None,
            row["pronunciation_provider"] is not None,
            row["pronunciation_model"] is not None,
            row["pronunciation_generated_at"] is not None,
        )
        for row in managed_rows
    )
    desired_unique_forms = _merge_desired_forms(
        desired_slots,
        slot_order=_managed_compacted_slot_order(context.paradigm_kind),
        lemma=context.lemma,
        exclude_lemma=context.paradigm_kind == "adjective",
    )
    desired_signature = sorted(
        (
            normalize_token(form.form) or form.form,
            "search",
            form.pos_tag,
            form.morphology,
            form.cor_ids,
            False,
            False,
            False,
            False,
            False,
        )
        for form in desired_unique_forms.values()
    )
    if current_signature == desired_signature:
        return _fix_variations_result(
            mutated=False,
            affected_forms=[],
            source_lexeme=source_lexeme,
            source_meaning=source_meaning,
        )

    affected_forms = [str(row["form"]) for row in managed_rows]
    affected_forms.extend(form.form for form in desired_unique_forms.values())
    for row in managed_rows:
        conn.execute("DELETE FROM surface_form_cor_variants WHERE surface_form_id = ?", (int(row["id"]),))
        conn.execute("DELETE FROM surface_forms WHERE id = ?", (int(row["id"]),))
    for desired_form in desired_unique_forms.values():
        surface_form_id = _insert_surface_form_row(
            conn,
            lexeme_id=context.lexeme_id,
            meaning_id=context.meaning_id,
            form=desired_form.form,
            pos_tag=desired_form.pos_tag,
            morphology=desired_form.morphology,
        )
        _insert_surface_form_cor_ids(conn, surface_form_id=surface_form_id, cor_ids=desired_form.cor_ids)

    return _fix_variations_result(
        mutated=True,
        affected_forms=affected_forms,
        source_lexeme=source_lexeme,
        source_meaning=source_meaning,
    )


def _resolve_fix_variations_slots(
    *,
    paradigm_kind: str,
    action: dict[str, object],
    fallback_slot_entries: dict[str, list[CORLocalEntry]],
    lemma: str,
) -> dict[str, tuple[DesiredParadigmVariationForm, ...]]:
    action_slot_form_lists = extract_fix_variations_action_slot_form_lists(action)
    action_slot_forms = extract_fix_variations_action_slot_forms(action)
    if not action_slot_form_lists and not action_slot_forms:
        return {}

    desired_slots: dict[str, tuple[DesiredParadigmVariationForm, ...]] = {}
    normalized_lemma = normalize_token(lemma) or lemma
    for slot_name in action_slot_labels_for_kind(paradigm_kind):
        fallback_entries = fallback_slot_entries.get(slot_name, [])
        if paradigm_kind == "adjective" and not fallback_entries and slot_name in {"plural_indefinite", "plural_definite"}:
            fallback_entries = fallback_slot_entries.get("plural_shared", [])
        desired_form_list = action_slot_form_lists.get(slot_name)
        if desired_form_list is None and slot_name == "singular_indefinite" and action_slot_form_lists:
            desired_form_list = [lemma]
        if desired_form_list is None and slot_name == "infinitive" and action_slot_form_lists:
            desired_form_list = [lemma]
        if desired_form_list is None and slot_name in action_slot_forms:
            desired_form_list = [action_slot_forms[slot_name]]
        if desired_form_list is None and (paradigm_kind != "noun" or slot_name != "singular_indefinite") and fallback_entries:
            desired_form_list = [entry.form for entry in fallback_entries]
        if desired_form_list is None:
            continue
        if slot_name in {"singular_indefinite", "singular_indefinite_n_word", "infinitive"}:
            desired_form_list = _ensure_lemma_in_slot_forms(desired_form_list, normalized_lemma)
        slot_forms = []
        for desired_form in desired_form_list:
            matching_entries = [
                entry for entry in fallback_entries if normalize_token(entry.form) == normalize_token(desired_form)
            ]
            matching_entry = matching_entries[0] if matching_entries else None
            fallback_entry = matching_entry or (fallback_entries[0] if fallback_entries else None)
            slot_forms.append(
                DesiredParadigmVariationForm(
                    form=desired_form,
                    pos_tag=fallback_entry.pos_tag if fallback_entry is not None else _default_pos_tag(paradigm_kind),
                    morphology=fallback_entry.morphology if fallback_entry is not None else None,
                    cor_ids=tuple(
                        dict.fromkeys(
                            cor_id
                            for cor_id in [
                                *(entry.cor_id for entry in matching_entries if entry.cor_id),
                                *((fallback_entry.cor_id,) if fallback_entry is not None and fallback_entry.cor_id else ()),
                            ]
                            if cor_id
                        )
                    ),
                )
            )
        desired_slots[slot_name] = tuple(slot_forms)
    return desired_slots


def _ensure_lemma_in_slot_forms(desired_form_list: list[str], lemma: str) -> list[str]:
    normalized_lemma = normalize_token(lemma) or lemma
    if any((normalize_token(item) or item) == normalized_lemma for item in desired_form_list):
        return desired_form_list
    return [lemma, *desired_form_list]


def _current_surface_form_cor_ids(conn: sqlite3.Connection, *, surface_form_id: int) -> tuple[str, ...]:
    rows = conn.execute(
        """
        SELECT cor_id
        FROM surface_form_cor_variants
        WHERE surface_form_id = ?
        ORDER BY id ASC
        """,
        (surface_form_id,),
    ).fetchall()
    return tuple(str(row["cor_id"]) for row in rows if row["cor_id"])


def _insert_surface_form_row(
    conn: sqlite3.Connection,
    *,
    lexeme_id: int,
    meaning_id: int,
    form: str,
    pos_tag: str | None,
    morphology: str | None,
) -> int:
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
        (lexeme_id, meaning_id, form, "search", 1, pos_tag, morphology),
    )
    surface_row = conn.execute(
        """
        SELECT id
        FROM surface_forms
        WHERE lexeme_id = ? AND meaning_id = ? AND form = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (lexeme_id, meaning_id, form),
    ).fetchone()
    if surface_row is None:
        raise RuntimeError("Failed to insert corrected variation.")
    return int(surface_row["id"])


def _insert_surface_form_cor_ids(
    conn: sqlite3.Connection,
    *,
    surface_form_id: int,
    cor_ids: tuple[str, ...],
) -> None:
    for cor_id in cor_ids:
        conn.execute(
            """
            INSERT OR IGNORE INTO surface_form_cor_variants (surface_form_id, cor_id)
            VALUES (?, ?)
            """,
            (surface_form_id, cor_id),
        )


def _merge_desired_forms(
    desired_slots: dict[str, tuple[DesiredParadigmVariationForm, ...]],
    *,
    slot_order: tuple[str, ...],
    lemma: str,
    exclude_lemma: bool,
) -> dict[str, DesiredParadigmVariationForm]:
    merged: dict[str, DesiredParadigmVariationForm] = {}
    normalized_lemma = normalize_token(lemma)
    for slot_name in slot_order:
        for form in desired_slots.get(slot_name, ()):
            normalized_form = normalize_token(form.form)
            if not normalized_form or (exclude_lemma and normalized_form == normalized_lemma):
                continue
            existing = merged.get(normalized_form)
            cor_ids = tuple(dict.fromkeys((*(existing.cor_ids if existing else ()), *form.cor_ids)))
            if existing is None:
                merged[normalized_form] = DesiredParadigmVariationForm(
                    form=form.form,
                    pos_tag=form.pos_tag,
                    morphology=form.morphology,
                    cor_ids=cor_ids,
                )
                continue
            merged[normalized_form] = DesiredParadigmVariationForm(
                form=existing.form,
                pos_tag=existing.pos_tag or form.pos_tag,
                morphology=existing.morphology or form.morphology,
                cor_ids=cor_ids,
            )
    return merged


def _current_row_slots(
    cor: CorResolutionCollaborator,
    *,
    context,
    form: str,
    pos_tag: str | None,
    morphology: str | None,
) -> tuple[str, ...]:
    entries = cor.cor_local_entries_for_form(
        form=form,
        lemma=context.lemma,
        preferred_pos_tag=_default_pos_tag(context.paradigm_kind),
        preferred_lemma_idx=context.cor_lemma_idx,
    )
    if entries:
        slots: list[str] = []
        for entry in entries:
            for slot in slots_for_entry(context.paradigm_kind, entry):
                if slot not in slots:
                    slots.append(slot)
        return tuple(slots)
    if paradigm_kind_from_pos_tag(pos_tag) != context.paradigm_kind:
        return ()
    return slots_for_gram_raw_and_morphology(
        context.paradigm_kind,
        gram_raw=None,
        morphology=morphology,
    )


def _fix_variations_result(
    *,
    mutated: bool,
    affected_forms: list[str],
    source_lexeme,
    source_meaning,
) -> VerificationActionExecutionResult:
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
    changed_forms = sorted({normalize_token(form) or form for form in affected_forms})
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


def _default_pos_tag(paradigm_kind: str) -> str:
    if paradigm_kind == "noun":
        return "NOUN"
    if paradigm_kind == "adjective":
        return "ADJ"
    return "VERB"


def _managed_compacted_slots(paradigm_kind: str) -> set[str]:
    if paradigm_kind == "adjective":
        return {*(ADJECTIVE_DISPLAY_SLOT_ORDER), "plural_shared"}
    return set(VERB_DISPLAY_SLOT_ORDER)


def _managed_compacted_slot_order(paradigm_kind: str) -> tuple[str, ...]:
    if paradigm_kind == "adjective":
        return (*ADJECTIVE_DISPLAY_SLOT_ORDER, "plural_shared")
    return VERB_DISPLAY_SLOT_ORDER
