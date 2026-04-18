from __future__ import annotations

import json

from app.services.verification_models import (
    WordVerificationAction,
    WordVerificationInput,
)
from app.services.verification_review_policy import (
    action_type_allowed,
    looks_like_danish_self_translation,
    should_discard_gloss_hint_translation_action,
    should_discard_move_to_lemma_action,
)
from app.services.verification_support import (
    is_valid_new_category,
    optional_clean_str,
    optional_clean_str_list,
)


def parse_batch_response(raw: str, expected_count: int) -> list[dict[str, object] | None]:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```").strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
    try:
        parsed = json.loads(cleaned)
    except ValueError:
        return [None] * expected_count
    if not isinstance(parsed, dict):
        return [None] * expected_count
    raw_results = parsed.get("results")
    if not isinstance(raw_results, list):
        return [None] * expected_count
    by_id: dict[int, dict[str, object]] = {}
    for item in raw_results:
        if not isinstance(item, dict):
            continue
        word_id = item.get("word_id")
        if isinstance(word_id, int):
            by_id[word_id] = item
    return [by_id.get(index) for index in range(expected_count)]


def parse_response(raw: str) -> dict[str, object]:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```").strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

    try:
        parsed = json.loads(cleaned)
    except ValueError:
        normalized = cleaned.lower()
        if "incorrect" in normalized or "error" in normalized or "mismatch" in normalized:
            return {"verdict": "incorrect", "word_count": None}
        return {"verdict": "correct", "word_count": None}

    if not isinstance(parsed, dict):
        return {"verdict": "incorrect", "word_count": None}

    verdict_value = parsed.get("verdict")
    word_count_value = parsed.get("word_count")
    verdict = verdict_value.strip().lower() if isinstance(verdict_value, str) else "incorrect"
    if verdict not in {"correct", "incorrect"}:
        verdict = "incorrect"
    word_count = word_count_value if isinstance(word_count_value, int) and word_count_value > 0 else None
    out: dict[str, object] = {"verdict": verdict, "word_count": word_count}
    if isinstance(parsed.get("problem"), str):
        out["problem"] = parsed["problem"]
    if isinstance(parsed.get("change_to_implement"), str):
        out["change_to_implement"] = parsed["change_to_implement"]
    if isinstance(parsed.get("existing_categories"), list):
        out["existing_categories"] = parsed["existing_categories"]
    if isinstance(parsed.get("new_categories"), list):
        out["new_categories"] = parsed["new_categories"]
    if parsed.get("new_category") is None or isinstance(parsed.get("new_category"), str):
        out["new_category"] = parsed.get("new_category")
    if isinstance(parsed.get("suggested_actions"), list):
        out["suggested_actions"] = parsed["suggested_actions"]
    return out


def parse_categories(parsed: dict[str, object], available_categories: tuple[str, ...]) -> list[str]:
    available_lookup = {" ".join(label.strip().split()).casefold(): label for label in available_categories}
    categories: list[str] = []
    seen: set[str] = set()
    raw_existing = parsed.get("existing_categories")
    if isinstance(raw_existing, list):
        for item in raw_existing:
            if not isinstance(item, str):
                continue
            normalized = " ".join(item.strip().split()).casefold()
            if not normalized or normalized in seen:
                continue
            matched = available_lookup.get(normalized)
            if matched is None:
                continue
            seen.add(normalized)
            categories.append(matched)
    raw_new_categories = parsed.get("new_categories")
    if isinstance(raw_new_categories, list):
        for item in raw_new_categories[:1]:
            if not isinstance(item, str):
                continue
            normalized_new = " ".join(item.strip().split())
            normalized_key = normalized_new.casefold()
            if (
                not is_valid_new_category(normalized_new)
                or normalized_key in seen
                or normalized_key in available_lookup
            ):
                continue
            seen.add(normalized_key)
            categories.append(normalized_new)
    elif isinstance(parsed.get("new_category"), str):
        normalized_new = " ".join(str(parsed["new_category"]).strip().split())
        normalized_key = normalized_new.casefold()
        if (
            is_valid_new_category(normalized_new)
            and normalized_key not in seen
            and normalized_key not in available_lookup
        ):
            seen.add(normalized_key)
            categories.append(normalized_new)
    return categories


def parse_suggested_actions(
    raw: object,
    payload: WordVerificationInput,
) -> list[WordVerificationAction]:
    if not isinstance(raw, list):
        return []
    actions: list[WordVerificationAction] = []
    for item in raw:
        action = normalize_action(item, payload)
        if action is not None:
            actions.append(action)
    return actions


def normalize_action(
    raw: object,
    payload: WordVerificationInput,
) -> WordVerificationAction | None:
    if not isinstance(raw, dict):
        return None
    action_type = raw.get("action_type")
    if not isinstance(action_type, str):
        return None
    normalized_type = action_type.strip().lower()
    if normalized_type not in {
        "fix_translation",
        "fix_variations",
        "move_to_meaning_section",
        "move_to_lemma",
    }:
        return None
    if not action_type_allowed(payload=payload, action_type=normalized_type):
        return None

    reason = optional_clean_str(raw.get("reason"))
    if normalized_type == "fix_variations":
        if payload.review_intent != "complete_variations":
            return None
        singular_indefinite_forms = tuple(optional_clean_str_list(raw.get("singular_indefinite_forms")))
        singular_indefinite_n_word_forms = tuple(optional_clean_str_list(raw.get("singular_indefinite_n_word_forms")))
        singular_indefinite_t_word_forms = tuple(optional_clean_str_list(raw.get("singular_indefinite_t_word_forms")))
        singular_definite_forms = tuple(optional_clean_str_list(raw.get("singular_definite_forms")))
        plural_indefinite_forms = tuple(optional_clean_str_list(raw.get("plural_indefinite_forms")))
        plural_definite_forms = tuple(optional_clean_str_list(raw.get("plural_definite_forms")))
        infinitive_forms = tuple(optional_clean_str_list(raw.get("infinitive_forms")))
        present_forms = tuple(optional_clean_str_list(raw.get("present_forms")))
        past_forms = tuple(optional_clean_str_list(raw.get("past_forms")))
        imperative_forms = tuple(optional_clean_str_list(raw.get("imperative_forms")))
        past_participle_forms = tuple(optional_clean_str_list(raw.get("past_participle_forms")))
        if not any(
            (
                singular_indefinite_forms,
                singular_indefinite_n_word_forms,
                singular_indefinite_t_word_forms,
                singular_definite_forms,
                plural_indefinite_forms,
                plural_definite_forms,
                infinitive_forms,
                present_forms,
                past_forms,
                imperative_forms,
                past_participle_forms,
            )
        ):
            return None
        return WordVerificationAction(
            action_type="fix_variations",
            reason=reason,
            singular_indefinite_forms=singular_indefinite_forms,
            singular_indefinite_n_word_forms=singular_indefinite_n_word_forms,
            singular_indefinite_t_word_forms=singular_indefinite_t_word_forms,
            singular_definite_forms=singular_definite_forms,
            plural_indefinite_forms=plural_indefinite_forms,
            plural_definite_forms=plural_definite_forms,
            infinitive_forms=infinitive_forms,
            present_forms=present_forms,
            past_forms=past_forms,
            imperative_forms=imperative_forms,
            past_participle_forms=past_participle_forms,
        )
    if payload.review_intent == "complete_variations":
        return None
    if normalized_type == "fix_translation":
        english_translation = optional_clean_str(raw.get("english_translation"))
        if not english_translation:
            return None
        if looks_like_danish_self_translation(english_translation=english_translation, payload=payload):
            return None
        if should_discard_gloss_hint_translation_action(
            english_translation=english_translation,
            payload=payload,
        ):
            return None
        return WordVerificationAction(
            action_type="fix_translation",
            reason=reason,
            english_translation=english_translation,
        )

    if normalized_type == "move_to_meaning_section":
        target_meaning_id = raw.get("target_meaning_id")
        if not isinstance(target_meaning_id, int):
            return None
        return WordVerificationAction(
            action_type="move_to_meaning_section",
            reason=reason,
            target_meaning_id=target_meaning_id,
        )

    target_lemma = optional_clean_str(raw.get("target_lemma"))
    target_meaning_key = optional_clean_str(raw.get("target_meaning_key"))
    if not target_lemma or not target_meaning_key:
        return None
    if should_discard_move_to_lemma_action(payload=payload, target_lemma=target_lemma):
        return None
    return WordVerificationAction(
        action_type="move_to_lemma",
        reason=reason,
        target_lemma=target_lemma,
        target_meaning_key=target_meaning_key,
        target_gloss=optional_clean_str(raw.get("target_gloss")),
        target_english_translation=optional_clean_str(raw.get("target_english_translation")),
        target_pos_tag=optional_clean_str(raw.get("target_pos_tag")),
        target_morphology=optional_clean_str(raw.get("target_morphology")),
    )
