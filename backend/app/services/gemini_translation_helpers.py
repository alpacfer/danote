from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.gemini_translation import (
        AlternativeTranslationsInput,
        BatchContextualWordTranslationRequestItem,
        ContextualWordTranslationInput,
        ExampleSentenceGenerationInput,
        MeaningSectionSelectionInput,
        NonCORVariationGenerationInput,
        NonCORWordGenerationInput,
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
        "sentence_context_da": payload.sentence_context,
        "sentence_context_target_marked_da": _mark_surface_in_sentence(payload.sentence_context, payload.surface_form),
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
        + "- If sentence_context_da is present, choose the English lemma or short phrase for this exact occurrence in that sentence.\n"
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
        "- If sentence_context_da is present, choose the English lemma or short phrase for this exact occurrence in that sentence.\n"
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
        "existing_examples_da": payload.existing_examples,
    }
    tense_rule = (
        f"- The verb must appear in the {payload.tense_label} form in the example sentence.\n"
        if payload.tense_label
        else ""
    )
    existing_rule = (
        "- Do NOT reuse or closely paraphrase any sentence in existing_examples_da; explore a different situation or angle.\n"
        if payload.existing_examples
        else ""
    )
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
        + tense_rule
        + existing_rule
        + f"Context:\n{json.dumps(context, ensure_ascii=False)}"
    )


_UD_MORPHOLOGY_RULES = (
    "- pos_tag is a Universal POS tag from {NOUN,VERB,ADJ,ADV,AUX,PRON,DET,ADP,CCONJ,SCONJ,PART,INTJ,NUM,X}.\n"
    "- morphology is a pipe-separated UD feature string using ONLY these keys and values:\n"
    "  Gender=Com|Neut, Number=Sing|Plur, Definite=Ind|Def, Case=Gen,\n"
    "  Degree=Pos|Cmp|Sup, VerbForm=Inf|Fin|Part, Tense=Pres|Past, Mood=Imp, Voice=Act|Pass,\n"
    "  PronType=Prs|Int, Poss=Yes, Person=1|2|3.\n"
    "- Lemma-level morphology examples by POS:\n"
    "    NOUN common gender → 'Gender=Com|Number=Sing|Definite=Ind'\n"
    "    NOUN neuter gender → 'Gender=Neut|Number=Sing|Definite=Ind'\n"
    "    ADJ → 'Degree=Pos'\n"
    "    VERB → 'VerbForm=Inf|Voice=Act'\n"
    "    ADV → 'Degree=Pos' (omit if not gradable)\n"
    "- surface_morphology must reflect the inflected form actually observed in sentence_context. Examples:\n"
    "    ADJ predicative common-gender singular → 'Degree=Pos|Gender=Com|Number=Sing|Definite=Ind'\n"
    "    NOUN definite singular → 'Gender=Com|Number=Sing|Definite=Def'\n"
    "    VERB present finite active → 'Tense=Pres|VerbForm=Fin|Voice=Act'\n"
    "- Use empty string '' (not 'adj' or freeform text) when no features apply.\n"
)


def build_non_cor_word_generation_prompt(payload: NonCORWordGenerationInput) -> str:
    return (
        "You are creating one Danish dictionary-style entry for a real Danish word that is missing from the source dictionary.\n"
        "If the surface form is not a valid Danish word, return JSON null.\n"
        "Otherwise return JSON only with this exact shape: "
        "{\"lemma\":\"...\",\"english_translation\":\"...\",\"meaning_key\":\"...\",\"gloss\":\"...\","
        "\"pos_tag\":\"NOUN|VERB|ADJ|ADV|AUX|PRON|DET|ADP|CCONJ|SCONJ|PART|INTJ|NUM|X\","
        "\"morphology\":\"...\",\"surface_pos_tag\":\"...\",\"surface_morphology\":\"...\"}\n"
        "Rules:\n"
        "- lemma must be the canonical lowercased Danish lemma.\n"
        "- english_translation must be the best short English translation for the intended sense.\n"
        "- meaning_key should be a stable lowercased key for this sense.\n"
        "- gloss should be a short lowercased English gloss for the exact sense.\n"
        + _UD_MORPHOLOGY_RULES +
        "- Use sentence_context to disambiguate the intended meaning and form.\n"
        "- With no sentence_context, validate the surface form as a standalone Danish word before creating an entry.\n"
        "- Do not invent extra senses.\n"
        "- Do not explain your reasoning.\n"
        f"Context:\n{json.dumps(asdict(payload), ensure_ascii=False)}"
    )


def build_batch_non_cor_word_generation_prompt(items: list[dict[str, object]]) -> str:
    return (
        "You are creating Danish dictionary-style entries for real Danish words that are missing from the source dictionary.\n"
        "Return JSON only with this exact shape: "
        "{\"items\":[{\"id\":\"0\",\"lemma\":\"...\",\"english_translation\":\"...\",\"meaning_key\":\"...\","
        "\"gloss\":\"...\",\"pos_tag\":\"ADJ\",\"morphology\":\"Degree=Pos\",\"surface_pos_tag\":\"ADJ\","
        "\"surface_morphology\":\"Degree=Pos|Gender=Com|Number=Sing|Definite=Ind\"}]}\n"
        "Rules:\n"
        "- Return exactly one item for every input id.\n"
        "- Copy each id exactly.\n"
        "- If a surface form is not a valid Danish word, return that item with null lemma and null translation fields.\n"
        "- lemma must be the canonical lowercased Danish lemma.\n"
        "- english_translation must be the best short English translation for the intended sense.\n"
        "- meaning_key should be a stable lowercased key for this sense.\n"
        "- gloss should be a short lowercased English gloss for the exact sense.\n"
        + _UD_MORPHOLOGY_RULES +
        "- Use sentence_context to disambiguate the intended meaning and form.\n"
        "- With no sentence_context, validate the surface form as a standalone Danish word before creating an entry.\n"
        "- Do not explain your reasoning.\n"
        f"Items:\n{json.dumps(items, ensure_ascii=False)}"
    )


def build_non_cor_variations_prompt(payload: NonCORVariationGenerationInput) -> str:
    slot_rules = _non_cor_variation_slot_rules(payload.pos_tag)
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
        f"{slot_rules}"
        "- If no additional forms are appropriate, return an empty forms array.\n"
        "- Do not explain your reasoning.\n"
        f"Context:\n{json.dumps(asdict(payload), ensure_ascii=False)}"
    )


def _non_cor_variation_slot_rules(pos_tag: str | None) -> str:
    normalized = str(pos_tag or "").upper()
    if normalized == "NOUN":
        return (
            "- For nouns, return only missing singular definite, plural indefinite, and plural definite forms.\n"
            "- Do not return genitive, derivational, or comparison-like forms.\n"
        )
    if normalized == "ADJ":
        return (
            "- For adjectives, return only positive-degree agreement forms: singular indefinite n-word, singular indefinite t-word, singular definite, plural indefinite, and plural definite.\n"
            "- Do not return comparative or superlative forms, including analytic forms with 'mere' or 'mest'.\n"
            "- Use Degree=Pos in adjective morphology, plus Gender/Number/Definite features for the agreement slot.\n"
        )
    if normalized == "VERB":
        return (
            "- For verbs, return only missing infinitive, present, past, imperative, and past participle forms.\n"
            "- Do not return nouns, adjectives, derived words, or multi-word tense phrases.\n"
        )
    return ""


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


from app.services.gemini_translation_parsing import (  # noqa: E402
    parse_alternative_translations_payload,
    parse_batch_meaning_section_payload,
    parse_batch_payload,
    parse_example_sentence_payload,
    parse_meaning_section_payload,
    parse_non_cor_variations_payload,
    parse_non_cor_word_entries_batch_payload,
    parse_non_cor_word_entry_payload,
    parse_translation,
)

__all__ = [
    "build_alternative_translations_prompt",
    "build_batch_meaning_section_selection_prompt",
    "build_batch_non_cor_word_generation_prompt",
    "build_batch_translation_prompt",
    "build_example_sentence_prompt",
    "build_meaning_section_selection_prompt",
    "build_non_cor_variations_prompt",
    "build_non_cor_word_generation_prompt",
    "is_retryable_exception",
    "normalize_translation_value",
    "parse_alternative_translations_payload",
    "parse_batch_meaning_section_payload",
    "parse_batch_payload",
    "parse_example_sentence_payload",
    "parse_meaning_section_payload",
    "parse_non_cor_variations_payload",
    "parse_non_cor_word_entries_batch_payload",
    "parse_non_cor_word_entry_payload",
    "parse_translation",
]
