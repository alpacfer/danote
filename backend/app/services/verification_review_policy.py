from __future__ import annotations

from typing import TYPE_CHECKING

from app.services.token_classifier import normalize_token

if TYPE_CHECKING:
    from app.services.verification import WordVerificationAction, WordVerificationInput


def looks_like_danish_self_translation(
    *,
    english_translation: str,
    payload: WordVerificationInput,
) -> bool:
    normalized_translation = normalize_token(english_translation)
    if not normalized_translation:
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
