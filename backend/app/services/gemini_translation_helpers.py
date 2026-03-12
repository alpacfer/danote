from __future__ import annotations

import json
from dataclasses import asdict
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from app.services.gemini_translation import (
        BatchContextualWordTranslationRequestItem,
        BatchContextualWordTranslationResponse,
        BatchContextualWordTranslationResponseItem,
        ContextualWordTranslationInput,
        MeaningSectionSelectionInput,
    )


def build_translation_prompt(payload: ContextualWordTranslationInput) -> str:
    context = {
        "surface_form_da": payload.surface_form,
        "lemma_da": payload.lemma,
        "pos_tag": payload.pos_tag,
        "morphology": payload.morphology,
        "gloss": payload.gloss,
        "lemma_translation_hint": payload.lemma_translation_hint,
        "gloss_translation_hint": payload.gloss_translation_hint,
    }
    has_dictionary_context = bool(
        payload.gloss
        or payload.pos_tag
        or payload.morphology
        or payload.lemma_translation_hint
        or payload.gloss_translation_hint
    )
    task_instruction = (
        "You translate Danish lemmas into the exact English lemma or short phrase that matches the supplied "
        "dictionary context.\n"
        "Translate lemma_da, and use surface_form_da, morphology, and gloss only for sense disambiguation.\n"
        if has_dictionary_context
        else "You translate a single Danish lemma into the exact English lemma or short phrase.\n"
        "Translate lemma_da, and use surface_form_da only as optional context.\n"
    )
    return (
        task_instruction
        + "Return JSON only: {\"translation\":\"...\"}\n"
        + "Rules:\n"
        + "- Output only the English translation.\n"
        + "- Translate lemma_da, not surface_form_da.\n"
        + "- Return a lemma-level translation; avoid adding articles/function words unless part of the lemma meaning.\n"
        + "- Treat pos_tag and morphology as hard constraints for sense disambiguation.\n"
        + "- If multiple senses are possible, choose the most common modern English meaning for the given Danish lemma/POS/morphology.\n"
        + "- Avoid false-friend transliterations and niche domain senses unless gloss or hints explicitly require them.\n"
        + "- For verbs, prefer the common infinitive meaning in English (for example, prefer 'to bend'/'to bow' over golf-specific 'to bogey' unless context explicitly indicates golf).\n"
        + "- Do not explain your reasoning.\n"
        + f"Context:\n{json.dumps(context, ensure_ascii=False)}"
    )


def build_batch_translation_prompt(items: list[BatchContextualWordTranslationRequestItem]) -> str:
    return (
        "You translate Danish lemmas into the exact English lemma or short phrase that matches the supplied "
        "dictionary context.\n"
        "For every item, translate lemma and use surface_form, morphology, and gloss only for sense disambiguation.\n"
        "Return JSON only with this exact shape: "
        "{\"items\":[{\"id\":\"0\",\"translation\":\"...\"}]}\n"
        "Rules:\n"
        "- Return exactly one item for every input id.\n"
        "- Copy each id exactly.\n"
        "- Output only the English translation.\n"
        "- Translate lemma, not surface_form.\n"
        "- Return lemma-level translations; avoid adding articles/function words unless part of the lemma meaning.\n"
        "- Treat pos_tag and morphology as hard constraints for sense disambiguation.\n"
        "- If multiple senses are possible, choose the most common modern English meaning for the given Danish lemma/POS/morphology.\n"
        "- Avoid false-friend transliterations and niche domain senses unless gloss or hints explicitly require them.\n"
        "- For verbs, prefer the common infinitive meaning in English (for example, prefer 'to bend'/'to bow' over golf-specific 'to bogey' unless context explicitly indicates golf).\n"
        "- Do not explain your reasoning.\n"
        f"Items:\n{json.dumps([asdict(item) for item in items], ensure_ascii=False)}"
    )


def build_meaning_section_selection_prompt(payload: MeaningSectionSelectionInput) -> str:
    context = {
        "surface_form_da": payload.surface_form,
        "lemma_da": payload.lemma,
        "pos_tag": payload.pos_tag,
        "morphology": payload.morphology,
        "gloss": payload.gloss,
        "english_translation": payload.english_translation,
    }
    candidates = [asdict(item) for item in payload.meaning_candidates]
    return (
        "You are assigning a Danish non-verb word to one existing meaning section.\n"
        "Return JSON only: {\"meaning_section_id\": <integer|null>}\n"
        "Rules:\n"
        "- Choose exactly one section id if there is a confident semantic match.\n"
        "- Use gloss, translation, POS, and morphology as hard disambiguation signals.\n"
        "- Return null if no section is a confident match.\n"
        "- Do not explain your reasoning.\n"
        f"Word context:\n{json.dumps(context, ensure_ascii=False)}\n"
        f"Meaning sections:\n{json.dumps(candidates, ensure_ascii=False)}"
    )


def is_retryable_exception(
    exc: Exception,
    *,
    exception_status_code: Callable[[Exception], int | None],
) -> bool:
    if isinstance(exc, (ImportError, ModuleNotFoundError, ValueError, TypeError, AttributeError)):
        return False
    status_code = exception_status_code(exc)
    if isinstance(status_code, int):
        return status_code in {408, 429, 500, 502, 503, 504}
    message = str(exc).lower()
    return any(
        token in message
        for token in (
            "timeout",
            "timed out",
            "connection reset",
            "connection aborted",
            "temporarily unavailable",
            "service unavailable",
            "rate limit",
            "429",
        )
    )


def normalize_translation_value(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.strip().split())
    return cleaned.lower() if cleaned else None


def _strip_code_fence(raw: str) -> str:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```").strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
    return cleaned


def parse_translation(raw: str | None) -> str | None:
    if not raw:
        return None
    cleaned = _strip_code_fence(raw)
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


def parse_batch_payload(payload: object, *, expected_ids: list[str]) -> BatchContextualWordTranslationResponse | None:
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
    if not isinstance(value, int) or value not in valid_ids:
        return None
    return value
