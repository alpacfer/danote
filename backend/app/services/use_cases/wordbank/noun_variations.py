from app.services.use_cases.wordbank.paradigm_variations import (
    ALL_NOUN_SLOTS,
    LEGACY_NOUN_SLOT_ACTION_FIELDS,
    NOUN_SLOT_ACTION_LIST_FIELDS,
    TARGET_NOUN_SLOTS,
    extract_fix_variations_action_slot_form_lists,
    extract_fix_variations_action_slot_forms,
    noun_meaning_context_from_rows,
    noun_slot_from_features,
    noun_slot_from_morphology,
    parse_fix_variations_text_slot_forms,
    resolve_target_noun_slot_entries,
)

__all__ = [
    "ALL_NOUN_SLOTS",
    "LEGACY_NOUN_SLOT_ACTION_FIELDS",
    "NOUN_SLOT_ACTION_LIST_FIELDS",
    "TARGET_NOUN_SLOTS",
    "extract_fix_variations_action_slot_form_lists",
    "extract_fix_variations_action_slot_forms",
    "noun_meaning_context_from_rows",
    "noun_slot_from_features",
    "noun_slot_from_morphology",
    "parse_fix_variations_text_slot_forms",
    "resolve_target_noun_slot_entries",
]
