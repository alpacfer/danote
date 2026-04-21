from __future__ import annotations

from app.api.schemas.v1.wordbank import VerificationAction
from app.services.verification import WordVerificationInput
from app.services.verification_review_policy import should_flag_missing_translation_review
from app.services.verification_review_text import TRANSLATION_FIX_CHANGE, TRANSLATION_FIX_PROBLEM


def supplement_missing_translation_actions(
    translation,
    *,
    payload: WordVerificationInput,
    verification_status: str,
    suggested_actions: list[VerificationAction],
) -> list[VerificationAction]:
    if verification_status != "flagged" or suggested_actions:
        return suggested_actions
    if not should_flag_missing_translation_review(payload=payload, suggested_actions=()):
        return suggested_actions
    translation_text = _resolve_missing_translation(translation, payload)
    if not translation_text:
        return suggested_actions
    return [
        VerificationAction(
            action_type="fix_translation",
            english_translation=translation_text,
            reason="Use the Gemini translation.",
        )
    ]


def translation_fix_copy_for_actions(
    suggested_actions: list[VerificationAction],
    problem: str | None,
    change_to_implement: str | None,
) -> tuple[str | None, str | None]:
    if any(action.action_type == "fix_translation" for action in suggested_actions):
        return TRANSLATION_FIX_PROBLEM, TRANSLATION_FIX_CHANGE
    return problem, change_to_implement


def _resolve_missing_translation(translation, payload: WordVerificationInput) -> str | None:
    surface_form = payload.stored_surface_form or _preferred_surface_form_for_translation(payload)
    contextual = translation.lookup_contextual_word_translation(
        surface_form=surface_form or payload.stored_lemma,
        lemma=payload.stored_lemma,
        pos_tag=(
            payload.selected_surface_pos_tag
            or payload.selected_meaning_pos_tag
            or payload.canonical_lemma_pos_tag
        ),
        morphology=(
            payload.selected_surface_morphology
            or payload.selected_meaning_morphology
            or payload.canonical_lemma_morphology
        ),
        gloss=payload.meaning_gloss,
        gloss_translation_hint=payload.meaning_gloss_translation,
    )
    translation_text = contextual.translation
    if not translation_text:
        return None
    if (payload.selected_meaning_pos_tag or payload.canonical_lemma_pos_tag) == "VERB" and not translation_text.startswith("to "):
        return f"to {translation_text}"
    return translation_text


def _preferred_surface_form_for_translation(payload: WordVerificationInput) -> str | None:
    for form in payload.available_surface_forms:
        if payload.meaning_id is not None and form.meaning_id != payload.meaning_id:
            continue
        if form.form != payload.stored_lemma:
            return form.form
    for form in payload.available_surface_forms:
        if payload.meaning_id is not None and form.meaning_id != payload.meaning_id:
            continue
        return form.form
    return None
