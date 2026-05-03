from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.services.gemini_translation import (
        AlternativeTranslationsInput,
        AlternativeTranslationsResult,
        BatchContextualWordTranslationRequestItem,
        BatchContextualWordTranslationResponse,
        BatchContextualWordTranslationResponseItem,
        ContextualWordTranslationInput,
        ExampleSentenceGenerationInput,
        MeaningSectionSelectionInput,
        NonCORVariationCandidate,
        NonCORVariationGenerationInput,
        NonCORVariationGenerationResult,
        NonCORWordGenerationInput,
        NonCORWordGenerationResult,
    )


def _danish_lemma_frame(lemma: str | None, pos_tag: str | None) -> str | None:
    normalized_lemma = " ".join((lemma or "").strip().split())
    normalized_pos = (pos_tag or "").strip().upper()
    if not normalized_lemma:
        return None
    if normalized_pos == "VERB":
        return f"at {normalized_lemma}"
    return normalized_lemma


def _mark_surface_in_sentence(sentence: str | None, surface_form: str | None) -> str | None:
    normalized_sentence = " ".join((sentence or "").strip().split())
    normalized_surface = " ".join((surface_form or "").strip().split())
    if not normalized_sentence or not normalized_surface:
        return None
    lower_sentence = normalized_sentence.lower()
    lower_surface = normalized_surface.lower()
    start = lower_sentence.find(lower_surface)
    if start == -1:
        return normalized_sentence
    end = start + len(normalized_surface)
    return f"{normalized_sentence[:start]}[{normalized_sentence[start:end]}]{normalized_sentence[end:]}"


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
    context = _meaning_section_context(payload)
    candidates = _meaning_section_candidates(payload)
    return (
        "You are assigning one Danish word occurrence from a sentence to one candidate meaning section.\n"
        "Return JSON only: {\"meaning_section_id\": <integer|null>}\n"
        "Rules:\n"
        "- Choose exactly one section id if one candidate clearly fits the target occurrence.\n"
        "- Use sentence_context_da and sentence_context_target_marked_da to identify the intended meaning of the target occurrence inside the full sentence.\n"
        "- Candidate options may differ by lemma, POS, and morphology even when the same Danish surface form can realize multiple words.\n"
        "- Use lemma, lemma_frame_da, gloss, english_translation, POS, and morphology as disambiguation signals.\n"
        "- Prefer the candidate whose POS/morphology best matches the target occurrence in the sentence.\n"
        "- Return null only if the candidates still cannot be distinguished confidently from the sentence and option data.\n"
        "- Do not explain your reasoning.\n"
        f"Word context:\n{json.dumps(context, ensure_ascii=False)}\n"
        f"Candidate meaning sections:\n{json.dumps(candidates, ensure_ascii=False)}"
    )


def build_batch_meaning_section_selection_prompt(
    items: list[dict[str, object]],
) -> str:
    return (
        "You are assigning multiple Danish word occurrences from one or more sentences to candidate meaning sections.\n"
        "Return JSON only with this exact shape: "
        "{\"items\":[{\"id\":\"0\",\"meaning_section_id\":123}]}\n"
        "Rules:\n"
        "- Return exactly one item for every input id.\n"
        "- Copy each id exactly.\n"
        "- Choose exactly one section id if one candidate clearly fits the target occurrence.\n"
        "- Return null only if the candidates still cannot be distinguished confidently from the sentence and option data.\n"
        "- Use sentence_context_da and sentence_context_target_marked_da to identify the intended meaning of the target occurrence inside the full sentence.\n"
        "- Candidate options may differ by lemma, POS, and morphology even when the same Danish surface form can realize multiple words.\n"
        "- Use lemma, lemma_frame_da, gloss, english_translation, POS, and morphology as disambiguation signals.\n"
        "- Prefer the candidate whose POS/morphology best matches the target occurrence in the sentence.\n"
        "- Do not explain your reasoning.\n"
        f"Items:\n{json.dumps(items, ensure_ascii=False)}"
    )


def _meaning_section_context(payload: MeaningSectionSelectionInput) -> dict[str, object]:
    return {
        "surface_form_da": payload.surface_form,
        "lemma_da": payload.lemma,
        "lemma_frame_da": _danish_lemma_frame(payload.lemma, payload.pos_tag),
        "pos_tag": payload.pos_tag,
        "morphology": payload.morphology,
        "gloss": payload.gloss,
        "english_translation": payload.english_translation,
        "sentence_context_da": payload.sentence_context,
        "sentence_context_target_marked_da": _mark_surface_in_sentence(payload.sentence_context, payload.surface_form),
    }
    

def _meaning_section_candidates(payload: MeaningSectionSelectionInput) -> list[dict[str, object]]:
    return [
        {
            **asdict(item),
            "lemma_frame_da": _danish_lemma_frame(item.lemma, item.pos_tag),
        }
        for item in payload.meaning_candidates
    ]


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


def build_example_sentence_prompt(payload: ExampleSentenceGenerationInput) -> str:
    context = {
        "stored_lemma_da": payload.stored_lemma,
        "lemma_frame_da": _danish_lemma_frame(payload.stored_lemma, payload.pos_tag),
        "meaning_id": payload.meaning_id,
        "meaning_key": payload.meaning_key,
        "gloss_da": payload.gloss,
        "gloss_translation_en": payload.gloss_translation,
        "english_translation_en": payload.english_translation,
        "additional_translations_en": payload.additional_translations,
        "pos_tag": payload.pos_tag,
        "morphology": payload.morphology,
        "cor_lemma_idx": payload.cor_lemma_idx,
        "saved_surface_forms_da": payload.surface_forms,
    }
    return (
        "You write one short Danish example sentence for a language-learning word card.\n"
        "Return JSON only with this exact shape: "
        "{\"source_text\":\"...\",\"english_translation\":\"...\"}\n"
        "Rules:\n"
        "- source_text must be one natural, short Danish sentence.\n"
        "- source_text must start with a lowercase letter.\n"
        "- source_text must not end with a period.\n"
        "- The sentence must explicitly include stored_lemma_da or one saved_surface_forms_da form.\n"
        "- The sentence must exemplify this exact saved meaning, not another homograph or related sense.\n"
        "- Use gloss, gloss_translation, english_translation, POS, morphology, and COR identity as hard sense context.\n"
        "- Keep the sentence simple enough for a learner; avoid names, obscure idioms, and long clauses.\n"
        "- english_translation must be a natural English translation of source_text.\n"
        "- Do not add explanations, alternatives, markdown, or quotes.\n"
        f"Context:\n{json.dumps(context, ensure_ascii=False)}"
    )


def build_non_cor_word_generation_prompt(payload: NonCORWordGenerationInput) -> str:
    return (
        "You are creating one Danish dictionary-style entry for a real Danish word that is missing from the source dictionary.\n"
        "Return JSON only with this exact shape: "
        "{\"lemma\":\"...\",\"english_translation\":\"...\",\"meaning_key\":\"...\",\"gloss\":\"...\","
        "\"pos_tag\":\"NOUN|VERB|ADJ|ADV|AUX|PRON|DET|ADP|CCONJ|SCONJ|PART|INTJ|NUM|X\","
        "\"morphology\":\"...\",\"surface_pos_tag\":\"...\",\"surface_morphology\":\"...\"}\n"
        "Rules:\n"
        "- lemma must be the canonical lowercased Danish lemma.\n"
        "- english_translation must be the best short English translation for the intended sense.\n"
        "- meaning_key should be a stable lowercased key for this sense.\n"
        "- gloss should be a short lowercased English gloss for the exact sense.\n"
        "- pos_tag and morphology describe the lemma/meaning.\n"
        "- surface_pos_tag and surface_morphology describe the observed surface form in context.\n"
        "- Use sentence_context to disambiguate the intended meaning and form.\n"
        "- Do not invent extra senses.\n"
        "- Do not explain your reasoning.\n"
        f"Context:\n{json.dumps(asdict(payload), ensure_ascii=False)}"
    )


def build_batch_non_cor_word_generation_prompt(items: list[dict[str, object]]) -> str:
    return (
        "You are creating Danish dictionary-style entries for real Danish words that are missing from the source dictionary.\n"
        "Return JSON only with this exact shape: "
        "{\"items\":[{\"id\":\"0\",\"lemma\":\"...\",\"english_translation\":\"...\",\"meaning_key\":\"...\","
        "\"gloss\":\"...\",\"pos_tag\":\"ADJ\",\"morphology\":\"...\",\"surface_pos_tag\":\"ADJ\","
        "\"surface_morphology\":\"...\"}]}\n"
        "Rules:\n"
        "- Return exactly one item for every input id.\n"
        "- Copy each id exactly.\n"
        "- lemma must be the canonical lowercased Danish lemma.\n"
        "- english_translation must be the best short English translation for the intended sense.\n"
        "- meaning_key should be a stable lowercased key for this sense.\n"
        "- gloss should be a short lowercased English gloss for the exact sense.\n"
        "- pos_tag and morphology describe the lemma/meaning.\n"
        "- surface_pos_tag and surface_morphology describe the observed surface form in context.\n"
        "- Use sentence_context to disambiguate the intended meaning and form.\n"
        "- Do not explain your reasoning.\n"
        f"Items:\n{json.dumps(items, ensure_ascii=False)}"
    )


def build_non_cor_variations_prompt(payload: NonCORVariationGenerationInput) -> str:
    return (
        "You are completing missing paradigm forms for one saved Danish meaning that is not present in the source dictionary.\n"
        "Return JSON only with this exact shape: "
        "{\"forms\":[{\"form\":\"...\",\"pos_tag\":\"ADJ\",\"morphology\":\"...\"}]}\n"
        "Rules:\n"
        "- Only return missing inflected forms for the same meaning.\n"
        "- Do not repeat any form already present in existing_forms.\n"
        "- Keep the same lemma, meaning, and part of speech.\n"
        "- Each form must be lowercased Danish text.\n"
        "- Include pos_tag and morphology for every returned form.\n"
        "- If no additional forms are appropriate, return an empty forms array.\n"
        "- Do not explain your reasoning.\n"
        f"Context:\n{json.dumps(asdict(payload), ensure_ascii=False)}"
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


def _normalize_example_source_text(value: object) -> str:
    source_text = normalize_translation_value(value)
    if source_text is None:
        return ""
    source_text = source_text.rstrip(".").strip()
    for index, char in enumerate(source_text):
        if char.isalpha():
            return f"{source_text[:index]}{char.lower()}{source_text[index + 1:]}"
    return source_text


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


def parse_non_cor_word_entry_payload(payload: object) -> NonCORWordGenerationResult | None:
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
) -> dict[str, NonCORWordGenerationResult | None] | None:
    items: Any = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return None
    expected = set(expected_ids)
    parsed: dict[str, NonCORWordGenerationResult | None] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = item.get("id")
        if not isinstance(item_id, str) or item_id not in expected:
            continue
        parsed[item_id] = parse_non_cor_word_entry_payload(item)
    return parsed


def parse_non_cor_variations_payload(payload: object) -> NonCORVariationGenerationResult | None:
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
