from app.services.use_cases.wordbank.paradigm_variations import noun_slot_from_morphology
from app.services.verification_paradigm_slots import (
    build_completion_review_paradigm_slot_context,
)


def build_completion_review_noun_slot_context(payload):
    return build_completion_review_paradigm_slot_context(payload)


__all__ = [
    "build_completion_review_noun_slot_context",
    "noun_slot_from_morphology",
]
