from __future__ import annotations

import json
from typing import Any

from app.services.gemini_translation_helpers import normalize_translation_value


def strip_code_fence(raw: str) -> str:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```").strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
    return cleaned


def parse_translation(raw: str | None) -> str | None:
    if not raw:
        return None
    cleaned = strip_code_fence(raw)
    try:
        parsed = json.loads(cleaned)
    except ValueError:
        return normalize_translation_value(cleaned)
    if isinstance(parsed, dict):
        value = parsed.get("translation")
        if isinstance(value, str):
            return normalize_translation_value(value)
    if isinstance(parsed, str):
        return normalize_translation_value(parsed)
    return None


def parse_batch_payload(payload: object, *, expected_ids: list[str]) -> object | None:
    from app.services.gemini_translation import (
        BatchContextualWordTranslationResponse,
        BatchContextualWordTranslationResponseItem,
    )

    if isinstance(payload, BatchContextualWordTranslationResponse):
        return payload
    items: Any = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return None

    expected = set(expected_ids)
    parsed_items: list[BatchContextualWordTranslationResponseItem] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = item.get("id")
        if not isinstance(item_id, str) or item_id not in expected:
            continue
        parsed_items.append(
            BatchContextualWordTranslationResponseItem(
                id=item_id,
                translation=normalize_translation_value(item.get("translation")),
            )
        )
    return BatchContextualWordTranslationResponse(items=parsed_items)


def parse_meaning_section_payload(payload: object, *, valid_ids: set[int]) -> int | None:
    if not isinstance(payload, dict):
        return None
    value = payload.get("meaning_section_id")
    if isinstance(value, str) and value.strip().isdigit():
        value = int(value.strip())
    if not isinstance(value, int) or value not in valid_ids:
        return None
    return value


def parse_batch_meaning_section_payload(
    payload: object,
    *,
    expected_ids: list[str],
    valid_ids_by_item: dict[str, set[int]],
) -> dict[str, int | None] | None:
    items: Any = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return None

    expected = set(expected_ids)
    parsed: dict[str, int | None] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = item.get("id")
        if not isinstance(item_id, str) or item_id not in expected:
            continue
        value = item.get("meaning_section_id")
        if isinstance(value, str) and value.strip().isdigit():
            value = int(value.strip())
        if value is None:
            parsed[item_id] = None
            continue
        if isinstance(value, int) and value in valid_ids_by_item.get(item_id, set()):
            parsed[item_id] = value
            continue
        parsed[item_id] = None
    return parsed


def parse_alternative_translations_payload(payload: object) -> object | None:
    from app.services.gemini_translation import AlternativeTranslationsResult

    if not isinstance(payload, dict):
        return None
    primary_translation = normalize_translation_value(payload.get("primary_translation"))
    raw_alternatives = payload.get("alternative_translations")
    if not isinstance(raw_alternatives, list):
        return None

    seen: set[str] = set()
    alternative_translations: list[str] = []
    for raw_value in raw_alternatives:
        normalized = normalize_translation_value(raw_value)
        if normalized is None or normalized == primary_translation or normalized in seen:
            continue
        seen.add(normalized)
        alternative_translations.append(normalized)

    return AlternativeTranslationsResult(
        primary_translation=primary_translation,
        alternative_translations=alternative_translations[:3],
    )


def parse_example_sentence_payload(payload: object) -> object | None:
    from app.services.gemini_translation import ExampleSentenceGenerationResult
    from app.services.use_cases.sentencebank_text import normalize_sentence_text

    if not isinstance(payload, dict):
        return None
    source_text = normalize_sentence_text(_normalize_example_source_text(payload.get("source_text")))
    english_translation = normalize_sentence_text(str(payload.get("english_translation") or ""))
    if not source_text or not english_translation:
        return None
    return ExampleSentenceGenerationResult(
        source_text=source_text,
        english_translation=english_translation,
    )


def parse_non_cor_word_entry_payload(payload: object) -> object | None:
    from app.services.gemini_translation import NonCORWordGenerationResult

    if not isinstance(payload, dict):
        return None
    lemma = _normalize_danish_value(payload.get("lemma"))
    if lemma is None:
        return None
    return NonCORWordGenerationResult(
        lemma=lemma,
        english_translation=normalize_translation_value(payload.get("english_translation")),
        meaning_key=_normalize_danish_value(payload.get("meaning_key")) or lemma,
        gloss=normalize_translation_value(payload.get("gloss")),
        pos_tag=_normalize_upper_value(payload.get("pos_tag")),
        morphology=_normalize_spaced_value(payload.get("morphology")),
        surface_pos_tag=_normalize_upper_value(payload.get("surface_pos_tag")),
        surface_morphology=_normalize_spaced_value(payload.get("surface_morphology")),
    )


def parse_non_cor_word_entries_batch_payload(
    payload: object,
    *,
    expected_ids: list[str],
) -> dict[str, object | None] | None:
    items: Any = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return None
    expected = set(expected_ids)
    parsed: dict[str, object | None] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = item.get("id")
        if not isinstance(item_id, str) or item_id not in expected:
            continue
        parsed[item_id] = parse_non_cor_word_entry_payload(item)
    return parsed


def parse_non_cor_variations_payload(payload: object) -> object | None:
    from app.services.gemini_translation import (
        NonCORVariationCandidate,
        NonCORVariationGenerationResult,
    )

    if not isinstance(payload, dict):
        return None
    raw_forms = payload.get("forms")
    if not isinstance(raw_forms, list):
        return None
    forms: list[NonCORVariationCandidate] = []
    seen: set[str] = set()
    for item in raw_forms:
        if not isinstance(item, dict):
            continue
        form = _normalize_danish_value(item.get("form"))
        if form is None or form in seen:
            continue
        seen.add(form)
        forms.append(
            NonCORVariationCandidate(
                form=form,
                pos_tag=_normalize_upper_value(item.get("pos_tag")),
                morphology=_normalize_spaced_value(item.get("morphology")),
            )
        )
    return NonCORVariationGenerationResult(forms=forms)


def _normalize_example_source_text(value: object) -> str:
    source_text = normalize_translation_value(value)
    if source_text is None:
        return ""
    source_text = source_text.rstrip(".").strip()
    for index, char in enumerate(source_text):
        if char.isalpha():
            return f"{source_text[:index]}{char.lower()}{source_text[index + 1:]}"
    return source_text


def _normalize_danish_value(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.strip().split()).lower()
    return cleaned or None


def _normalize_upper_value(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip().upper()
    return cleaned or None


def _normalize_spaced_value(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.strip().split())
    return cleaned or None
