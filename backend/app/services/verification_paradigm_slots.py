from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.verification import WordVerificationInput


def build_paradigm_slot_context(payload: WordVerificationInput) -> dict[str, list[str]]:
    paradigm_kind = _paradigm_kind_from_pos_tag(payload.selected_meaning_pos_tag)
    if paradigm_kind == "noun":
        return _build_noun_slot_context(payload)
    if paradigm_kind == "adjective":
        return _build_adjective_slot_context(payload)
    if paradigm_kind == "verb":
        return _build_verb_slot_context(payload)
    return {}


def build_completion_review_paradigm_slot_context(payload: WordVerificationInput) -> dict[str, list[str]]:
    return build_paradigm_slot_context(payload)


def _build_noun_slot_context(payload: WordVerificationInput) -> dict[str, list[str]]:
    slot_forms: dict[str, list[str]] = {}
    for form in payload.available_surface_forms:
        if form.meaning_id != payload.meaning_id:
            continue
        for slot in _slots_for_gram_raw_and_morphology("noun", gram_raw=form.gram_raw, morphology=form.morphology):
            slot_forms.setdefault(slot, []).append(form.form)
    singular_indefinite = slot_forms.setdefault("singular_indefinite", [])
    if payload.stored_lemma not in singular_indefinite:
        singular_indefinite.insert(0, payload.stored_lemma)
    return {slot: _dedupe(forms) for slot, forms in slot_forms.items() if forms}


def _build_adjective_slot_context(payload: WordVerificationInput) -> dict[str, list[str]]:
    slot_forms: dict[str, list[str]] = {
        "singular_indefinite_n_word": [payload.stored_lemma],
    }
    for form in payload.available_surface_forms:
        if form.meaning_id != payload.meaning_id:
            continue
        for slot in _slots_for_gram_raw_and_morphology("adjective", gram_raw=form.gram_raw, morphology=form.morphology):
            slot_forms.setdefault(slot, []).append(form.form)
            if slot == "plural_shared":
                slot_forms.setdefault("plural_indefinite", []).append(form.form)
                slot_forms.setdefault("plural_definite", []).append(form.form)
    return {slot: _dedupe(forms) for slot, forms in slot_forms.items() if forms}


def _build_verb_slot_context(payload: WordVerificationInput) -> dict[str, list[str]]:
    slot_forms: dict[str, list[str]] = {
        "infinitive": [payload.stored_lemma],
    }
    for form in payload.available_surface_forms:
        if form.meaning_id != payload.meaning_id:
            continue
        for slot in _slots_for_gram_raw_and_morphology("verb", gram_raw=form.gram_raw, morphology=form.morphology):
            slot_forms.setdefault(slot, []).append(form.form)
    return {slot: _dedupe(forms) for slot, forms in slot_forms.items() if forms}


def _dedupe(forms: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for form in forms:
        if form in seen:
            continue
        seen.add(form)
        deduped.append(form)
    return deduped


def _paradigm_kind_from_pos_tag(pos_tag: str | None) -> str | None:
    from app.services.use_cases.wordbank.paradigm_variations import paradigm_kind_from_pos_tag

    return paradigm_kind_from_pos_tag(pos_tag)


def _slots_for_gram_raw_and_morphology(
    paradigm_kind: str,
    *,
    gram_raw: str | None,
    morphology: str | None,
) -> tuple[str, ...]:
    from app.services.use_cases.wordbank.paradigm_variations import slots_for_gram_raw_and_morphology

    return slots_for_gram_raw_and_morphology(
        paradigm_kind,
        gram_raw=gram_raw,
        morphology=morphology,
    )
