from __future__ import annotations

from app.api.schemas.v1.wordbank import VerificationAction
from app.services.use_cases.wordbank.paradigm_variations import (
    extract_fix_variations_action_slot_form_lists,
)
from app.services.verification import WordVerificationAction, WordVerificationInput


def verification_action_to_schema(action: WordVerificationAction) -> VerificationAction:
    return VerificationAction(
        action_type=action.action_type,
        reason=action.reason,
        english_translation=action.english_translation,
        singular_indefinite_forms=list(action.singular_indefinite_forms) or None,
        singular_indefinite_n_word_forms=list(action.singular_indefinite_n_word_forms) or None,
        singular_indefinite_t_word_forms=list(action.singular_indefinite_t_word_forms) or None,
        singular_definite_forms=list(action.singular_definite_forms) or None,
        plural_indefinite_forms=list(action.plural_indefinite_forms) or None,
        plural_definite_forms=list(action.plural_definite_forms) or None,
        infinitive_forms=list(action.infinitive_forms) or None,
        present_forms=list(action.present_forms) or None,
        past_forms=list(action.past_forms) or None,
        imperative_forms=list(action.imperative_forms) or None,
        past_participle_forms=list(action.past_participle_forms) or None,
        target_meaning_id=action.target_meaning_id,
        target_lemma=action.target_lemma,
        target_meaning_key=action.target_meaning_key,
        target_gloss=action.target_gloss,
        target_english_translation=action.target_english_translation,
        target_pos_tag=action.target_pos_tag,
        target_morphology=action.target_morphology,
    )


def rethink_categories_message(stored_lemma: str, applied_categories: list[str]) -> str:
    if not applied_categories:
        return f"Updated categories for '{stored_lemma}'. No categories are currently assigned."
    if len(applied_categories) == 1:
        return f"Updated categories for '{stored_lemma}' to {applied_categories[0]}."
    return f"Updated categories for '{stored_lemma}'."


def normalize_review_intent(review_intent: str) -> str:
    normalized = review_intent.strip().lower() if isinstance(review_intent, str) else "general"
    if normalized == "complete_variations":
        return "complete_variations"
    return "general"


def completion_review_actions(
    *,
    payload: WordVerificationInput,
    verification_status: str,
    suggested_actions: list[VerificationAction],
    problem: str | None,
    change_to_implement: str | None,
) -> list[VerificationAction]:
    if (
        payload.review_intent != "complete_variations"
        or payload.meaning_id is None
        or verification_status != "flagged"
    ):
        return suggested_actions
    for action in suggested_actions:
        if action.action_type != "fix_variations":
            continue
        action_payload = action.model_dump(exclude_none=True)
        action_slot_form_lists = extract_fix_variations_action_slot_form_lists(action_payload)
        if action_slot_form_lists:
            return [action]
    return []


def find_fix_variations_action_form_lists(actions: list[dict[str, object]]) -> dict[str, list[str]]:
    for candidate in actions:
        if candidate.get("action_type") != "fix_variations":
            continue
        slot_form_lists = extract_fix_variations_action_slot_form_lists(candidate)
        if slot_form_lists:
            return slot_form_lists
    return {}
