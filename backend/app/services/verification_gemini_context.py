from __future__ import annotations

from app.services.verification_models import WordVerificationInput
from app.services.verification_paradigm_slots import (
    build_completion_review_paradigm_slot_context,
    build_paradigm_slot_context,
)
from app.services.verification_review_policy import should_expose_translation_hint
from app.services.verification_support import category_surface_forms, verification_surface_forms


def verification_context(payload: WordVerificationInput) -> dict[str, object]:
    paradigm_slot_surface_forms = build_paradigm_slot_context(payload)
    return {
        "current_entry": {
            "review_intent": payload.review_intent,
            "scope_type": "meaning_section" if payload.meaning_id is not None else "lemma_root",
            "lemma": payload.stored_lemma,
            "surface_form": payload.stored_surface_form,
            "meaning_id": payload.meaning_id,
            "meaning_key": payload.meaning_key,
            "gloss": payload.meaning_gloss,
            "selected_translation": payload.selected_translation,
            "selected_translation_scope": payload.selected_translation_scope,
            "lexeme_source": payload.lexeme_source,
            "surface_source": payload.surface_source,
            "canonical_lemma": payload.canonical_lemma,
            "canonical_lemma_pos_tag": payload.canonical_lemma_pos_tag,
            "canonical_lemma_morphology": payload.canonical_lemma_morphology,
            "selected_meaning_pos_tag": payload.selected_meaning_pos_tag,
            "selected_meaning_morphology": payload.selected_meaning_morphology,
            "selected_surface_pos_tag": payload.selected_surface_pos_tag,
            "selected_surface_morphology": payload.selected_surface_morphology,
            "selected_surface_gram_raw": selected_surface_gram_raw(payload),
            "translation_hint": (
                payload.meaning_gloss_translation if should_expose_translation_hint(payload) else None
            ),
        },
        "available_meaning_sections": [
            {
                "id": section.id,
                "meaning_key": section.meaning_key,
                "gloss_translation": section.gloss_translation,
                "english_translation": section.english_translation,
                "pos_tag": section.pos_tag,
            }
            for section in payload.sibling_meaning_sections
        ],
        "relevant_surface_forms": [
            {
                "form": form.form,
                "meaning_id": form.meaning_id,
                "meaning_key": form.meaning_key,
                "gloss": form.gloss,
                "gloss_translation": form.gloss_translation,
                "english_translation": form.english_translation,
                "pos_tag": form.pos_tag,
                "morphology": form.morphology,
                "gram_raw": form.gram_raw,
            }
            for form in verification_surface_forms(payload)
        ],
        "paradigm_slot_surface_forms": paradigm_slot_surface_forms,
        "noun_slot_surface_forms": build_completion_review_paradigm_slot_context(payload)
        if payload.review_intent == "complete_variations"
        else {},
    }


def category_context(payload: WordVerificationInput) -> dict[str, object]:
    return {
        "current_entry": {
            "scope_type": "meaning_section" if payload.meaning_id is not None else "lemma_root",
            "lemma": payload.stored_lemma,
            "surface_form": payload.stored_surface_form,
            "meaning_id": payload.meaning_id,
            "meaning_key": payload.meaning_key,
            "gloss": payload.meaning_gloss,
            "gloss_translation": payload.meaning_gloss_translation,
            "selected_translation": payload.selected_translation,
            "selected_translation_scope": payload.selected_translation_scope,
            "canonical_lemma": payload.canonical_lemma,
            "selected_meaning_pos_tag": payload.selected_meaning_pos_tag,
            "selected_surface_pos_tag": payload.selected_surface_pos_tag,
            "current_categories": list(payload.current_categories),
        },
        "available_categories": list(payload.available_categories),
        "available_meaning_sections": [
            {
                "id": section.id,
                "meaning_key": section.meaning_key,
                "gloss_translation": section.gloss_translation,
                "english_translation": section.english_translation,
            }
            for section in payload.sibling_meaning_sections
        ],
        "relevant_surface_forms": [
            {
                "form": form.form,
                "meaning_id": form.meaning_id,
                "meaning_key": form.meaning_key,
                "gloss_translation": form.gloss_translation,
                "english_translation": form.english_translation,
                "pos_tag": form.pos_tag,
                "morphology": form.morphology,
            }
            for form in category_surface_forms(payload)
        ],
    }


def selected_surface_gram_raw(payload: WordVerificationInput) -> str | None:
    if not payload.stored_surface_form:
        return None
    for form in payload.available_surface_forms:
        if form.form == payload.stored_surface_form and form.meaning_id == payload.meaning_id:
            return form.gram_raw
    return None
