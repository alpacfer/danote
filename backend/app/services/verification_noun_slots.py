from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.verification import WordVerificationInput


def build_completion_review_noun_slot_context(payload: WordVerificationInput) -> dict[str, list[str]]:
    slot_forms: dict[str, list[str]] = {}
    for form in payload.available_surface_forms:
        if form.meaning_id != payload.meaning_id:
            continue
        slot = noun_slot_from_morphology(form.morphology)
        if slot is None:
            continue
        slot_forms.setdefault(slot, []).append(form.form)
    singular_indefinite = slot_forms.setdefault("singular_indefinite", [])
    if payload.stored_lemma not in singular_indefinite:
        singular_indefinite.insert(0, payload.stored_lemma)
    return slot_forms


def noun_slot_from_morphology(morphology: str | None) -> str | None:
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
