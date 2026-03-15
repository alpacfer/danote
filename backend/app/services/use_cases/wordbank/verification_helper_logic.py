from __future__ import annotations

from app.api.schemas.v1.wordbank import VerificationAction
from app.services.use_cases.wordbank.noun_variations import (
    NOUN_SLOT_ACTION_FIELDS,
    extract_fix_variations_action_slot_forms,
    parse_fix_variations_text_slot_forms,
)
from app.services.verification import WordVerificationAction, WordVerificationInput


def verification_action_to_schema(action: WordVerificationAction) -> VerificationAction:
    return VerificationAction(
        action_type=action.action_type,
        reason=action.reason,
        english_translation=action.english_translation,
        gloss=action.gloss,
        singular_definite_form=action.singular_definite_form,
        plural_indefinite_form=action.plural_indefinite_form,
        plural_definite_form=action.plural_definite_form,
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
    text_slot_forms = (
        parse_fix_variations_text_slot_forms(change_to_implement)
        or parse_fix_variations_text_slot_forms(problem)
    )
    enriched_actions: list[VerificationAction] = []
    fix_variations_found = False
    for action in suggested_actions:
        if action.action_type != "fix_variations":
            enriched_actions.append(action)
            continue
        fix_variations_found = True
        action_slot_forms = extract_fix_variations_action_slot_forms(action.model_dump(exclude_none=True))
        merged_slot_forms = action_slot_forms or text_slot_forms
        enriched_actions.append(
            action.model_copy(
                update={
                    "singular_definite_form": merged_slot_forms.get("singular_definite"),
                    "plural_indefinite_form": merged_slot_forms.get("plural_indefinite"),
                    "plural_definite_form": merged_slot_forms.get("plural_definite"),
                }
            )
        )
    if fix_variations_found:
        return enriched_actions
    return [
        VerificationAction(
            action_type="fix_variations",
            reason="Replace the completed variation set with the reviewed noun forms for this meaning.",
            singular_definite_form=text_slot_forms.get("singular_definite"),
            plural_indefinite_form=text_slot_forms.get("plural_indefinite"),
            plural_definite_form=text_slot_forms.get("plural_definite"),
        ),
        *enriched_actions,
    ]


def find_fix_variations_action_fields(actions: list[dict[str, object]]) -> dict[str, str]:
    for candidate in actions:
        if candidate.get("action_type") != "fix_variations":
            continue
        slot_forms = extract_fix_variations_action_slot_forms(candidate)
        if slot_forms:
            return slot_forms
    return {}
