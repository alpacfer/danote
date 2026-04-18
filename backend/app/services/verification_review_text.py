from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.verification import WordVerificationAction


TRANSLATION_FIX_PROBLEM = "The English translation does not match the saved meaning."
TRANSLATION_FIX_CHANGE = "Set the translation to the saved meaning."
MISSING_TRANSLATION_PROBLEM = "The English translation is missing."
MISSING_TRANSLATION_CHANGE = "Add an English translation for this entry."


def normalize_translation_review_copy(
    *,
    problem: str | None,
    change_to_implement: str | None,
    suggested_actions: tuple[WordVerificationAction, ...],
) -> tuple[str | None, str | None]:
    if any(action.action_type == "fix_translation" for action in suggested_actions):
        return TRANSLATION_FIX_PROBLEM, TRANSLATION_FIX_CHANGE
    return problem, change_to_implement


def should_suppress_gloss_only_feedback(
    *,
    problem: str | None,
    change_to_implement: str | None,
    suggested_actions: tuple[WordVerificationAction, ...],
) -> bool:
    if suggested_actions:
        return False
    prose = " ".join(part for part in (problem, change_to_implement) if isinstance(part, str)).casefold()
    if not prose:
        return False
    return "gloss" in prose
