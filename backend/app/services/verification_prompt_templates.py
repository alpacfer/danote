from __future__ import annotations

import json


def build_word_verification_prompt(
    *,
    entry: dict[str, object],
    completion_review: bool,
    surface_form_review: bool,
    allowed_action_types: tuple[str, ...],
) -> str:
    if completion_review:
        action_examples = (
            '{"action_type":"fix_variations","reason":"...",'
            '"singular_indefinite_forms":["...", "..."],'
            '"singular_indefinite_n_word_forms":["..."],'
            '"singular_indefinite_t_word_forms":["..."],'
            '"singular_definite_forms":["..."],'
            '"plural_indefinite_forms":["..."],'
            '"plural_definite_forms":["..."],'
            '"infinitive_forms":["..."],'
            '"present_forms":["..."],'
            '"past_forms":["..."],'
            '"imperative_forms":["..."],'
            '"past_participle_forms":["..."]}'
        )
        fix_variations_rule = (
            "- If the reviewed meaning is a noun, include the complete noun variation set in singular_indefinite_forms, singular_definite_forms, plural_indefinite_forms, and plural_definite_forms whenever those slots are known.\n"
            "- For noun reviews, singular_indefinite_forms must include the saved lemma and any alternative spellings that belong in that same slot.\n"
            "- If the reviewed meaning is an adjective, include agreement forms in singular_indefinite_n_word_forms, singular_indefinite_t_word_forms, singular_definite_forms, plural_indefinite_forms, and plural_definite_forms whenever those slots are known.\n"
            "- For adjective reviews, use n-word / t-word terminology throughout.\n"
            "- If the reviewed meaning is a verb, include infinitive_forms, present_forms, past_forms, imperative_forms, and past_participle_forms whenever those slots are known.\n"
        )
    else:
        action_examples = (
            '{"action_type":"fix_translation","reason":"...","english_translation":"..."},'
            '{"action_type":"move_to_meaning_section","reason":"...","target_meaning_id":0},'
            '{"action_type":"move_to_lemma","reason":"...","target_lemma":"...",'
            '"target_meaning_key":"...","target_gloss":"...",'
            '"target_english_translation":"...","target_pos_tag":"...",'
            '"target_morphology":"..."}'
        )
        fix_variations_rule = ""
        general_action_examples_by_type = {
            "fix_translation": '{"action_type":"fix_translation","reason":"...","english_translation":"..."}',
            "move_to_meaning_section": '{"action_type":"move_to_meaning_section","reason":"...","target_meaning_id":0}',
            "move_to_lemma": (
                '{"action_type":"move_to_lemma","reason":"...","target_lemma":"...",'
                '"target_meaning_key":"...","target_gloss":"...",'
                '"target_english_translation":"...","target_pos_tag":"...",'
                '"target_morphology":"..."}'
            ),
        }
        action_examples = ",".join(
            general_action_examples_by_type[action_type]
            for action_type in allowed_action_types
            if action_type in general_action_examples_by_type
        )
    action_type_rule = (
        f"- Use only these action types: {', '.join(allowed_action_types)}.\n"
        if not completion_review
        else "- Use only this action type: fix_variations.\n"
    )
    variation_scope_rule = (
        "- This is normal save verification. Verify only whether the saved lemma/meaning/surface placement is correct.\n"
        "- Do not require missing paradigm forms or suggest adding/correcting other variations here. Variation completeness is handled only by the Complete variations workflow.\n"
        if not completion_review
        else "- This review was triggered by Complete variations. Keep the saved lemma and meaning section fixed; verify whether the saved surface forms are valid variations for that lemma in this meaning.\n"
        "- If canonical_lemma differs from lemma during Complete variations review, treat that as a clue to re-check the completed variation set only.\n"
        "- When the completed variation set is wrong, describe the surface-form problem in problem/change_to_implement and use action_type=fix_variations.\n"
    )
    canonical_rule = (
        "- If canonical_lemma is present and differs from lemma, treat the saved lemma as incorrect and suggest move_to_lemma to canonical_lemma unless the entry already belongs under another provided lemma.\n"
        if not completion_review
        else ""
    )
    surface_scope_rule = (
        "- This target is a saved surface form review. Do not suggest translation fixes for this scope.\n"
        "- Treat the saved meaning_id, selected_surface_pos_tag, selected_surface_morphology, selected_surface_gram_raw, relevant_surface_forms, and paradigm_slot_surface_forms as hard constraints.\n"
        "- Homographs are common. A surface form may be valid here even if the same spelling exists as a different lemma or part of speech elsewhere.\n"
        if surface_form_review and not completion_review
        else "- This target is a lemma or meaning review. Translation fixes may apply only at this scope.\n"
        "- Treat canonical_lemma, selected_meaning_pos_tag, relevant_surface_forms, and paradigm_slot_surface_forms as hard evidence for whether the current lemma already fits.\n"
        "- If translation_hint is present and the current lemma/meaning is otherwise morphologically coherent, prefer fix_translation instead of move_to_lemma.\n"
        if not completion_review
        else ""
    )
    return (
        "You are a Professional Danish Language Expert.\n"
        "Review one saved wordbank target.\n"
        "Translations belong to the lemma or meaning section only.\n"
        "Surface forms do not have independent translations.\n"
        "Glosses are sense labels. Never suggest editing a gloss.\n"
        "Use the reviewed target, relevant surface forms, and sibling meanings only as needed.\n"
        "Count if the reviewed entry is composed of multiple words.\n"
        "Return JSON only.\n"
        "{"
        '"verdict":"correct|incorrect",'
        '"word_count":0,'
        '"problem":"...",'
        '"change_to_implement":"...",'
        '"suggested_actions":['
        f"{action_examples}"
        "]}\n"
        "Rules:\n"
        f"{action_type_rule}"
        "- If verdict=correct, return suggested_actions as [].\n"
        "- If action_type=move_to_meaning_section, target_meaning_id must be one of the available meaning ids.\n"
        "- If action_type=move_to_lemma, include target_lemma and target_meaning_key.\n"
        "- Never propose gloss edits; use gloss only to identify the intended meaning section.\n"
        "- If action_type=fix_translation, english_translation must be idiomatic English. Never repeat the Danish lemma or surface form unless the translated gloss explicitly matches it.\n"
        "- When gram_raw or paradigm_slot_surface_forms identify a valid paradigm slot for the saved surface form, do not move that form to a different lemma just because the spelling is also a noun or another homograph elsewhere.\n"
        f"{fix_variations_rule}"
        '- Keep message short: use "OK" or "Review needed".\n'
        "- Keep problem to one short sentence.\n"
        "- Keep change_to_implement to one short imperative sentence.\n"
        "- When meaning_gloss_translation or section gloss_translation is present, use it as the main sense clue for homographs.\n"
        f"{surface_scope_rule}"
        f"{variation_scope_rule}"
        f"{canonical_rule}"
        "- Suggested actions must be self-contained. Do not rely on prose fields for apply details.\n"
        f"Entry:\n{json.dumps(entry, ensure_ascii=False)}"
    )


def build_word_category_prompt(*, entry: dict[str, object]) -> str:
    return (
        "You are a Professional Danish Language Expert.\n"
        "Classify one saved wordbank scope into broad semantic categories.\n"
        "Prefer matching existing categories whenever they fit.\n"
        "Return JSON only.\n"
        "{"
        '"existing_categories":["..."],'
        '"new_categories":["..."]'
        "}\n"
        "Rules:\n"
        "- existing_categories must be chosen from available_categories.\n"
        "- existing_categories may include multiple items, but never duplicates.\n"
        "- Return at most 1 new_categories item, and only when no existing category fits.\n"
        "- New categories must be broad, reusable, and user-facing. Never return morphology, part-of-speech, or overly narrow labels.\n"
        "- If existing categories fully cover the scope, return new_categories as [] or omit it.\n"
        f"Entry:\n{json.dumps(entry, ensure_ascii=False)}"
    )
