from __future__ import annotations

from typing import TYPE_CHECKING

from app.services.token_classifier import normalize_token
from app.services.verification_paradigm_slots import build_paradigm_slot_context
from app.services.verification_support import verification_surface_forms

if TYPE_CHECKING:
    from app.services.verification import WordVerificationAction, WordVerificationInput


def is_surface_form_review(payload: WordVerificationInput) -> bool:
    return payload.review_intent != "complete_variations" and bool(normalize_token(payload.stored_surface_form or ""))


def allowed_general_action_types(payload: WordVerificationInput) -> tuple[str, ...]:
    if payload.review_intent == "complete_variations":
        return ("fix_variations",)
    if is_surface_form_review(payload):
        action_types = ["move_to_lemma"]
        if payload.meaning_id is not None:
            action_types.insert(0, "move_to_meaning_section")
        return tuple(action_types)
    return ("fix_translation", "move_to_lemma")


def action_type_allowed(*, payload: WordVerificationInput, action_type: str) -> bool:
    return action_type in allowed_general_action_types(payload)


def looks_like_danish_self_translation(
    *,
    english_translation: str,
    payload: WordVerificationInput,
) -> bool:
    normalized_translation = normalize_token(english_translation)
    if not normalized_translation:
        return True
    if _is_low_confidence_verb_self_translation(
        english_translation=english_translation,
        payload=payload,
    ):
        return True
    normalized_gloss_translation = normalize_token(payload.meaning_gloss_translation or "")
    if not normalized_gloss_translation:
        return False
    for candidate in (payload.stored_lemma, payload.stored_surface_form):
        normalized_candidate = normalize_token(candidate or "")
        if (
            normalized_candidate
            and normalized_translation == normalized_candidate
            and normalized_translation != normalized_gloss_translation
        ):
            return True
    return False


def should_expose_translation_hint(payload: WordVerificationInput) -> bool:
    if not normalize_token(payload.meaning_gloss_translation or ""):
        return False
    if not normalize_token(payload.selected_translation or ""):
        return True
    return _is_low_confidence_verb_self_translation(
        english_translation=payload.selected_translation or "",
        payload=payload,
    )


def should_discard_gloss_hint_translation_action(
    *,
    english_translation: str,
    payload: WordVerificationInput,
) -> bool:
    normalized_translation = normalize_token(english_translation)
    normalized_gloss_translation = normalize_token(payload.meaning_gloss_translation or "")
    normalized_selected_translation = normalize_token(payload.selected_translation or "")
    if not normalized_translation or not normalized_gloss_translation or not normalized_selected_translation:
        return False
    if normalized_translation != normalized_gloss_translation:
        return False
    if normalized_selected_translation == normalized_gloss_translation:
        return False
    return not should_expose_translation_hint(payload)


def should_ignore_variation_only_review(
    *,
    payload: WordVerificationInput,
    raw_suggested_actions: object,
    suggested_actions: tuple[WordVerificationAction, ...],
) -> bool:
    if payload.review_intent == "complete_variations" or suggested_actions:
        return False
    if not isinstance(raw_suggested_actions, list):
        return False
    raw_types = [
        item.get("action_type", "").strip().lower()
        for item in raw_suggested_actions
        if isinstance(item, dict) and isinstance(item.get("action_type"), str)
    ]
    if not raw_types:
        return False
    supported_non_variation = {"fix_translation", "move_to_meaning_section", "move_to_lemma"}
    return "fix_variations" in raw_types and not any(action_type in supported_non_variation for action_type in raw_types)


def should_ignore_surface_translation_review(
    *,
    payload: WordVerificationInput,
    raw_suggested_actions: object,
    suggested_actions: tuple[WordVerificationAction, ...],
    problem: str | None,
    change_to_implement: str | None,
) -> bool:
    if not is_surface_form_review(payload) or suggested_actions:
        return False

    raw_types = [
        item.get("action_type", "").strip().lower()
        for item in raw_suggested_actions
        if isinstance(raw_suggested_actions, list)
        and isinstance(item, dict)
        and isinstance(item.get("action_type"), str)
    ]
    if raw_types and all(action_type == "fix_translation" for action_type in raw_types):
        return True

    prose = " ".join(part for part in (problem, change_to_implement) if isinstance(part, str)).casefold()
    if not prose:
        return False
    return "translation" in prose


def should_ignore_gloss_hint_translation_review(
    *,
    payload: WordVerificationInput,
    raw_suggested_actions: object,
    suggested_actions: tuple[WordVerificationAction, ...],
) -> bool:
    if suggested_actions or is_surface_form_review(payload) or payload.review_intent == "complete_variations":
        return False
    if not isinstance(raw_suggested_actions, list):
        return False

    raw_fix_translations = [
        item
        for item in raw_suggested_actions
        if isinstance(item, dict) and isinstance(item.get("action_type"), str)
    ]
    if not raw_fix_translations:
        return False
    if any(item.get("action_type", "").strip().lower() != "fix_translation" for item in raw_fix_translations):
        return False
    return all(
        isinstance(item.get("english_translation"), str)
        and should_discard_gloss_hint_translation_action(
            english_translation=str(item["english_translation"]),
            payload=payload,
        )
        for item in raw_fix_translations
    )


def should_discard_move_to_lemma_action(
    *,
    payload: WordVerificationInput,
    target_lemma: str,
) -> bool:
    if payload.review_intent == "complete_variations":
        return False
    normalized_target = normalize_token(target_lemma)
    normalized_stored = normalize_token(payload.stored_lemma)
    normalized_canonical = normalize_token(payload.canonical_lemma or payload.stored_lemma)
    if not normalized_target or normalized_target == normalized_stored:
        return True
    if normalized_canonical != normalized_stored:
        return False
    slot_context = build_paradigm_slot_context(payload)
    if not slot_context:
        return False
    relevant_forms = verification_surface_forms(payload)
    if is_surface_form_review(payload):
        normalized_surface = normalize_token(payload.stored_surface_form or "")
        if not normalized_surface:
            return False
        has_matching_surface = any(
            normalize_token(form.form) == normalized_surface
            and form.meaning_id == payload.meaning_id
            and _form_matches_selected_surface_metadata(form=form, payload=payload)
            and _slot_context_contains_form(slot_context, normalized_surface)
            for form in relevant_forms
        )
        return has_matching_surface
    if payload.meaning_id is None:
        return False
    meaning_forms = [
        form
        for form in relevant_forms
        if form.meaning_id == payload.meaning_id and _form_matches_selected_meaning_metadata(form=form, payload=payload)
    ]
    if not meaning_forms:
        return False
    return any(
        form.gram_raw or form.morphology
        for form in meaning_forms
    )


def should_backfill_translation_from_gloss_hint(
    *,
    payload: WordVerificationInput,
    raw_suggested_actions: object,
    suggested_actions: tuple[WordVerificationAction, ...],
) -> bool:
    if payload.review_intent == "complete_variations" or is_surface_form_review(payload):
        return False
    if payload.meaning_id is None or suggested_actions:
        return False
    if normalize_token(payload.canonical_lemma or payload.stored_lemma) != normalize_token(payload.stored_lemma):
        return False
    if not should_expose_translation_hint(payload):
        return False
    if isinstance(raw_suggested_actions, list):
        raw_types = [
            item.get("action_type", "").strip().lower()
            for item in raw_suggested_actions
            if isinstance(item, dict) and isinstance(item.get("action_type"), str)
        ]
        if raw_types and all(action_type == "move_to_lemma" for action_type in raw_types):
            return should_discard_move_to_lemma_action(
                payload=payload,
                target_lemma=next(
                    (
                        item.get("target_lemma", "")
                        for item in raw_suggested_actions
                        if isinstance(item, dict)
                    ),
                    "",
                ),
            )
    return False


def should_force_translation_fix_from_gloss_hint(
    *,
    payload: WordVerificationInput,
    suggested_actions: tuple[WordVerificationAction, ...],
) -> bool:
    if payload.review_intent == "complete_variations" or is_surface_form_review(payload):
        return False
    if normalize_token(payload.canonical_lemma or payload.stored_lemma) != normalize_token(payload.stored_lemma):
        return False
    if not should_expose_translation_hint(payload):
        return False
    return not any(action.action_type == "fix_translation" for action in suggested_actions)


def should_ignore_morphology_supported_move_review(
    *,
    payload: WordVerificationInput,
    raw_suggested_actions: object,
    suggested_actions: tuple[WordVerificationAction, ...],
) -> bool:
    if suggested_actions or not isinstance(raw_suggested_actions, list):
        return False
    raw_moves = [
        item
        for item in raw_suggested_actions
        if isinstance(item, dict) and isinstance(item.get("action_type"), str)
    ]
    if not raw_moves:
        return False
    if any(item.get("action_type", "").strip().lower() != "move_to_lemma" for item in raw_moves):
        return False
    return any(
        should_discard_move_to_lemma_action(
            payload=payload,
            target_lemma=str(item.get("target_lemma", "")),
        )
        for item in raw_moves
    )


def _slot_context_contains_form(slot_context: dict[str, list[str]], normalized_form: str) -> bool:
    return any(
        normalize_token(form) == normalized_form
        for forms in slot_context.values()
        for form in forms
    )


def _form_matches_selected_surface_metadata(*, form, payload: WordVerificationInput) -> bool:
    if payload.selected_surface_pos_tag and form.pos_tag and form.pos_tag != payload.selected_surface_pos_tag:
        return False
    if payload.selected_surface_morphology and form.morphology and form.morphology != payload.selected_surface_morphology:
        return False
    return True


def _form_matches_selected_meaning_metadata(*, form, payload: WordVerificationInput) -> bool:
    if payload.selected_meaning_pos_tag and form.pos_tag and form.pos_tag != payload.selected_meaning_pos_tag:
        return False
    return True


def _is_low_confidence_verb_self_translation(
    *,
    english_translation: str,
    payload: WordVerificationInput,
) -> bool:
    pos_tag = (payload.selected_meaning_pos_tag or payload.canonical_lemma_pos_tag or "").strip().upper()
    if pos_tag != "VERB":
        return False
    normalized_translation = normalize_token(english_translation)
    normalized_lemma = normalize_token(payload.stored_lemma)
    return normalized_translation in {normalized_lemma, f"to {normalized_lemma}"}
