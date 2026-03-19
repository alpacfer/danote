from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.verification import WordVerificationInput


def build_completion_review_paradigm_slot_context(payload: WordVerificationInput) -> dict[str, list[str]]:
    paradigm_kind = _paradigm_kind_from_pos_tag(payload.selected_meaning_pos_tag)
    if paradigm_kind == "noun":
        return _build_noun_slot_context(payload)
    if paradigm_kind == "adjective":
        return _build_adjective_slot_context(payload)
    return {}


def _build_noun_slot_context(payload: WordVerificationInput) -> dict[str, list[str]]:
    slot_forms: dict[str, list[str]] = {}
    for form in payload.available_surface_forms:
        if form.meaning_id != payload.meaning_id:
            continue
        slot = _noun_slot_from_morphology(form.morphology)
        if slot is None:
            continue
        slot_forms.setdefault(slot, []).append(form.form)
    singular_indefinite = slot_forms.setdefault("singular_indefinite", [])
    if payload.stored_lemma not in singular_indefinite:
        singular_indefinite.insert(0, payload.stored_lemma)
    return slot_forms


def _build_adjective_slot_context(payload: WordVerificationInput) -> dict[str, list[str]]:
    slot_forms: dict[str, list[str]] = {
        "singular_indefinite_n_word": [payload.stored_lemma],
    }
    for form in payload.available_surface_forms:
        if form.meaning_id != payload.meaning_id:
            continue
        for slot in _adjective_slots_for_form(form.gram_raw, form.morphology):
            slot_forms.setdefault(slot, []).append(form.form)
            if slot == "plural_shared":
                slot_forms.setdefault("plural_indefinite", []).append(form.form)
                slot_forms.setdefault("plural_definite", []).append(form.form)
    return {slot: _dedupe(forms) for slot, forms in slot_forms.items() if forms}


def _paradigm_kind_from_pos_tag(pos_tag: str | None) -> str | None:
    normalized = str(pos_tag or "").upper()
    if normalized == "NOUN":
        return "noun"
    if normalized == "ADJ":
        return "adjective"
    return None


def _noun_slot_from_morphology(morphology: str | None) -> str | None:
    if not morphology:
        return None
    if "Number=Sing" in morphology and "Definite=Ind" in morphology:
        return "singular_indefinite"
    if "Number=Sing" in morphology and "Definite=Def" in morphology:
        return "singular_definite"
    if "Number=Plur" in morphology and "Definite=Ind" in morphology:
        return "plural_indefinite"
    if "Number=Plur" in morphology and "Definite=Def" in morphology:
        return "plural_definite"
    return None


def _adjective_slot_from_morphology(morphology: str | None) -> str | None:
    if not morphology:
        return None
    if "Number=Sing" in morphology and "Definite=Ind" in morphology and "Gender=Neut" in morphology:
        return "singular_indefinite_t_word"
    if "Number=Sing" in morphology and "Definite=Ind" in morphology:
        return "singular_indefinite_n_word"
    if "Number=Sing" in morphology and "Definite=Def" in morphology:
        return "singular_definite"
    if "Number=Plur" in morphology:
        return "plural_shared"
    return None


def _adjective_slots_for_form(gram_raw: str | None, morphology: str | None) -> list[str]:
    slots: list[str] = []
    for gram in _split_gram_parts(gram_raw):
        parts = set(gram.split("."))
        if "adj" not in parts:
            continue
        if {"sg", "ubest", "fk"}.issubset(parts):
            slots.append("singular_indefinite_n_word")
        if {"sg", "ubest", "itk"}.issubset(parts):
            slots.append("singular_indefinite_t_word")
        if {"sg", "best"}.issubset(parts):
            slots.append("singular_definite")
        if "pl" in parts:
            slots.append("plural_shared")
    if slots:
        return _dedupe(slots)
    slot = _adjective_slot_from_morphology(morphology)
    return [slot] if slot else []


def _split_gram_parts(gram_raw: str | None) -> list[str]:
    if not gram_raw:
        return []
    return [part.strip().lower() for part in gram_raw.split("|") if part.strip()]


def _dedupe(forms: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for form in forms:
        if form in seen:
            continue
        seen.add(form)
        deduped.append(form)
    return deduped
