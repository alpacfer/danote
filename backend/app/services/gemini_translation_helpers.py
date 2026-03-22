from __future__ import annotations

import json
from dataclasses import asdict
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from app.services.gemini_translation import (
        AlternativeTranslationsInput,
        AlternativeTranslationsResult,
        BatchContextualWordTranslationRequestItem,
        BatchContextualWordTranslationResponse,
        BatchContextualWordTranslationResponseItem,
        ContextualWordTranslationInput,
        MeaningSectionSelectionInput,
    )


def _danish_lemma_frame(lemma: str | None, pos_tag: str | None) -> str | None:
    normalized_lemma = " ".join((lemma or "").strip().split())
    normalized_pos = (pos_tag or "").strip().upper()
    if not normalized_lemma:
        return None
    if normalized_pos == "VERB":
        return f"at {normalized_lemma}"
    return normalized_lemma


def build_translation_prompt(payload: ContextualWordTranslationInput) -> str:
    lemma_frame = _danish_lemma_frame(payload.lemma, payload.pos_tag)
    context = {
        "surface_form_da": payload.surface_form,
        "lemma_da": payload.lemma,
        "lemma_frame_da": lemma_frame,
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
    has_gloss_context = bool(payload.gloss or payload.gloss_translation_hint)
    task_instruction = (
        "You translate Danish lemmas into the exact English lemma or short phrase that matches the supplied "
        "dictionary context.\n"
        "Translate lemma_da, and use surface_form_da, morphology, and gloss only for sense disambiguation.\n"
        if has_dictionary_context
        else "You translate a single Danish lemma into the exact English lemma or short phrase.\n"
        "Translate lemma_da, and use surface_form_da only as optional context.\n"
    )
    glossless_search_rules = (
        ""
        if has_gloss_context
        else "- This may be a search-quality fallback after another translator returned a Danish-looking echo; prefer the real English meaning over transliteration.\n"
        "- If lemma_frame_da is present, interpret it as the canonical Danish dictionary form to translate.\n"
        "- For Danish verbs, treat lemma_frame_da like an infinitive such as 'at bile' and return the English infinitive meaning.\n"
        "- Do not copy the Danish lemma into English framing such as 'to bile' unless the ordinary English lemma is genuinely the same word.\n"
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
        + glossless_search_rules
        + "- Do not explain your reasoning.\n"
        + f"Context:\n{json.dumps(context, ensure_ascii=False)}"
    )


def build_batch_translation_prompt(items: list[BatchContextualWordTranslationRequestItem]) -> str:
    has_gloss_context = any(item.gloss or item.gloss_translation_hint for item in items)
    glossless_search_rules = (
        ""
        if has_gloss_context
        else "- Some items may be search-quality fallbacks after another translator echoed the Danish lemma; prefer the real English meaning over transliteration.\n"
        "- If an item has lemma_frame_da, interpret it as the canonical Danish dictionary form to translate.\n"
        "- For Danish verbs, treat lemma_frame_da like an infinitive such as 'at bile' and return the English infinitive meaning.\n"
        "- Do not copy the Danish lemma into English framing such as 'to bile' unless the ordinary English lemma is genuinely the same word.\n"
    )
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
        + glossless_search_rules
        + "- Do not explain your reasoning.\n"
        + f"Items:\n{json.dumps([{**asdict(item), 'lemma_frame_da': _danish_lemma_frame(item.lemma, item.pos_tag)} for item in items], ensure_ascii=False)}"
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


def build_alternative_translations_prompt(payload: AlternativeTranslationsInput) -> str:
    context = {
        "surface_form_da": payload.surface_form,
        "lemma_da": payload.lemma,
        "lemma_frame_da": _danish_lemma_frame(payload.lemma, payload.pos_tag),
        "pos_tag": payload.pos_tag,
        "morphology": payload.morphology,
        "gloss": payload.gloss,
        "current_translation_en": payload.current_translation,
        "existing_additional_translations_en": payload.existing_additional_translations,
    }
    return (
        "You review one saved Danish wordbank meaning and decide whether the existing English translation should stay, "
        "be corrected, or gain a few very common alternative translations.\n"
        "Return JSON only with this exact shape: "
        "{\"primary_translation\":\"...\",\"alternative_translations\":[\"...\"]}\n"
        "Rules:\n"
        "- Translate the Danish lemma/sense into modern, common English only.\n"
        "- Use gloss, pos_tag, and morphology as hard sense-disambiguation context.\n"
        "- primary_translation should be the single best common dictionary-style English translation for this exact sense.\n"
        "- If the current translation is already the best common translation, repeat it as primary_translation.\n"
        "- If the current translation is wrong, unnatural, or less common for this sense, replace it with a better common translation.\n"
        "- alternative_translations must contain only obvious, popular alternatives for the same sense.\n"
        "- Return at most 3 alternative translations.\n"
        "- Do not include niche, archaic, technical, speculative, or sentence-level paraphrases.\n"
        "- Do not include duplicates, inflection-only variants, or the same value as primary_translation.\n"
        "- For verbs, prefer English infinitive form.\n"
        "- If there are no common alternatives, return an empty alternative_translations array.\n"
        "- Do not explain your reasoning.\n"
        f"Context:\n{json.dumps(context, ensure_ascii=False)}"
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


def parse_alternative_translations_payload(payload: object) -> AlternativeTranslationsResult | None:
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
