from __future__ import annotations

import os
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.api.schemas.v1.wordbank import (
    ENPosGroup,
    ENSearchFormResponse,
    ENSenseOut,
    ResolveQueryResponse,
)
from app.services.en_local import ENLocalLexiconService
from app.services.translation import TranslationService
from app.services.use_cases.static_presaved_words import (
    StaticPresavedWord,
    static_presaved_word_for_english,
)
from app.services.use_cases.static_pronouns import StaticPronoun, static_pronoun_for_english
from app.services.use_cases.wordbank.collaborators.en_local_translations import (
    translate_en_lemma_contextual,
)

_POS_ORDER = {"NOUN": 0, "VERB": 1, "ADJ": 2, "ADV": 3, "PROPN": 4}
_MAX_SENSES_PER_POS = 5


def _normalize_translation_candidate(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.strip().split())
    return normalized or None


def _translate_en_surface_form(
    *,
    form: str,
    translation_service: TranslationService | None,
    cache: dict[str, str | None],
) -> str | None:
    normalized_form = _normalize_translation_candidate(form)
    if not normalized_form or translation_service is None:
        return None
    cache_key = normalized_form.lower()
    if cache_key in cache:
        return cache[cache_key]
    try:
        result = translation_service.translate_en_to_da(normalized_form)
    except Exception:
        result = None
    normalized_result = _normalize_translation_candidate(result)
    if normalized_result and normalized_result.lower() == normalized_form.lower():
        normalized_result = None
    cache[cache_key] = normalized_result
    return normalized_result


def resolve_en_query(
    *,
    normalized_query: str,
    en_local_lexicon_service: ENLocalLexiconService,
    en_gemini_translation_service,
    translation_service: TranslationService | None,
    include_translations: bool,
) -> ResolveQueryResponse:
    groups = build_en_pos_groups(
        normalized_query=normalized_query,
        en_local_lexicon_service=en_local_lexicon_service,
        en_gemini_translation_service=en_gemini_translation_service,
        translation_service=translation_service,
        include_translations=include_translations,
    )

    primary_group = next((group for group in groups if group.danish_translation), None)
    primary_translation = primary_group.danish_translation if primary_group is not None else None
    primary_lemma = primary_group.lemma if primary_group is not None else None
    primary_pos = primary_group.pos_ud if primary_group is not None else None
    resolved_lemma = primary_lemma or (groups[0].lemma if groups else None)
    resolved_surface = normalized_query

    return ResolveQueryResponse(
        query_surface=normalized_query,
        query_lemma=resolved_lemma,
        classification="new",
        matched_lemma=None,
        matched_lemma_summary=None,
        query_pos_tag=primary_pos,
        query_morphology=None,
        resolved_surface=primary_translation or resolved_surface,
        resolved_lemma=primary_translation or resolved_lemma,
        da_to_en_translation=None,
        en_to_da_translation=primary_translation,
        en_to_da_lemma=primary_translation,
        en_to_da_pos_tag=primary_pos,
        en_to_da_morphology=None,
        query_language="en",
        query_language_confidence=0.95,
        word_actions=[],
        en_pos_groups=groups,
    )


def search_en_form(
    *,
    form: str,
    en_local_lexicon_service: ENLocalLexiconService | None,
    en_gemini_translation_service,
    translation_service: TranslationService | None,
    include_translations: bool,
) -> ENSearchFormResponse:
    normalized_form = _normalize_translation_candidate(form) or ""
    static_pronoun = static_pronoun_for_english(normalized_form)
    if static_pronoun is not None:
        return static_pronoun_en_search_response(normalized_form, static_pronoun)
    static_presaved_word = static_presaved_word_for_english(normalized_form)
    if static_presaved_word is not None:
        return static_presaved_word_en_search_response(normalized_form, static_presaved_word)
    if en_local_lexicon_service is None or not normalized_form:
        return ENSearchFormResponse(form=normalized_form, groups=[])
    return ENSearchFormResponse(
        form=normalized_form,
        groups=build_en_pos_groups(
            normalized_query=normalized_form,
            en_local_lexicon_service=en_local_lexicon_service,
            en_gemini_translation_service=en_gemini_translation_service,
            translation_service=translation_service,
            include_translations=include_translations,
        ),
    )


def static_pronoun_en_search_response(form: str, pronoun: StaticPronoun) -> ENSearchFormResponse:
    return ENSearchFormResponse(
        form=form,
        groups=[
            ENPosGroup(
                lemma=form,
                form=form,
                pos_ud="PRON",
                pos_raw="pronoun",
                danish_translation=pronoun.lemma,
                meaning_description=pronoun.english_translation,
                senses=[
                    ENSenseOut(
                        pos_ud="PRON",
                        sense_idx=1,
                        gloss=pronoun.english_translation,
                        danish_translation=pronoun.lemma,
                        examples=[],
                    )
                ],
            )
        ],
    )


def static_presaved_word_en_search_response(form: str, word: StaticPresavedWord) -> ENSearchFormResponse:
    pos_tag = word.pos_tag or "X"
    return ENSearchFormResponse(
        form=form,
        groups=[
            ENPosGroup(
                lemma=form,
                form=form,
                pos_ud=pos_tag,
                pos_raw=pos_tag.lower(),
                danish_translation=word.lemma,
                meaning_description=word.english_translation,
                senses=[
                    ENSenseOut(
                        pos_ud=pos_tag,
                        sense_idx=1,
                        gloss=word.english_translation,
                        danish_translation=word.lemma,
                        examples=[],
                    )
                ],
            )
        ],
    )


def build_en_pos_groups(
    *,
    normalized_query: str,
    en_local_lexicon_service: ENLocalLexiconService,
    en_gemini_translation_service,
    translation_service: TranslationService | None,
    include_translations: bool,
) -> list[ENPosGroup]:
    matches = en_local_lexicon_service.lookup_form(normalized_query)
    groups_by_key: OrderedDict[tuple[str, str], ENPosGroup] = OrderedDict()
    translation_cache: dict[tuple[str, str, str], str | None] = {}
    surface_translation_cache: dict[str, str | None] = {}

    sorted_matches = sorted(
        matches,
        key=lambda m: (_POS_ORDER.get(m.pos_ud, 99), m.lemma.lower()),
    )

    group_inputs: list[tuple[object, list[object], tuple[str, str], bool]] = []
    for match in sorted_matches:
        key = (match.lemma.lower(), match.pos_ud)
        if key in groups_by_key or any(existing_key == key for _, _, existing_key, _ in group_inputs):
            continue
        senses = en_local_lexicon_service.lookup_lemma_senses(match.lemma, match.pos_ud)
        if not senses:
            continue
        senses = senses[:_MAX_SENSES_PER_POS]
        form_is_inflected = match.form.strip().lower() != match.lemma.strip().lower()
        group_inputs.append((match, senses, key, form_is_inflected))

    group_translations: dict[tuple[str, str], str | None] = {}
    if include_translations:
        group_translations = _initial_group_translations(
            normalized_query=normalized_query,
            group_inputs=group_inputs,
            en_gemini_translation_service=en_gemini_translation_service,
            translation_service=translation_service,
            translation_cache=translation_cache,
            surface_translation_cache=surface_translation_cache,
        )

    for match, senses, key, _form_is_inflected in group_inputs:
        sense_outs: list[ENSenseOut] = []
        group_translation: str | None = None
        if include_translations:
            group_translation = group_translations.get(key)
        for sense in senses:
            translation_value = group_translation
            if include_translations and not translation_value:
                translation_value = translate_en_lemma_contextual(
                    lemma=match.lemma,
                    pos_ud=match.pos_ud,
                    gloss=sense.gloss,
                    gemini_service=en_gemini_translation_service,
                    translation_service=translation_service,
                    cache=translation_cache,
                )
                translation_value = _normalize_translation_candidate(translation_value)
                if translation_value and translation_value.lower() == match.lemma.lower():
                    translation_value = None
            if not group_translation and translation_value:
                group_translation = translation_value
            sense_outs.append(
                ENSenseOut(
                    pos_ud=sense.pos_ud,
                    sense_idx=sense.sense_idx,
                    gloss=sense.gloss,
                    danish_translation=translation_value,
                    examples=sense.examples,
                )
            )
        group = ENPosGroup(
            lemma=match.lemma,
            form=match.form,
            pos_ud=match.pos_ud,
            pos_raw=senses[0].pos_raw if senses else None,
            danish_translation=group_translation,
            senses=sense_outs,
        )
        groups_by_key[key] = group

    groups = list(groups_by_key.values())
    if include_translations:
        _attach_disambiguation_descriptions(
            normalized_query=normalized_query,
            groups=groups,
            en_gemini_translation_service=en_gemini_translation_service,
        )
    return groups


def _initial_group_translations(
    *,
    normalized_query: str,
    group_inputs: list[tuple[object, list[object], tuple[str, str], bool]],
    en_gemini_translation_service,
    translation_service: TranslationService | None,
    translation_cache: dict[tuple[str, str, str], str | None],
    surface_translation_cache: dict[str, str | None],
) -> dict[tuple[str, str], str | None]:
    if _flag_enabled("DANOTE_SEARCH_BATCHED_GEMINI", default=False):
        batched = _initial_group_translations_batched(
            normalized_query=normalized_query,
            group_inputs=group_inputs,
            en_gemini_translation_service=en_gemini_translation_service,
        )
        if batched is not None:
            return batched
    if not _flag_enabled("DANOTE_SEARCH_PARALLEL", default=True) or len(group_inputs) < 2:
        return {
            key: _initial_group_translation(
                match=match,
                senses=senses,
                form_is_inflected=form_is_inflected,
                en_gemini_translation_service=en_gemini_translation_service,
                translation_service=translation_service,
                translation_cache=translation_cache,
                surface_translation_cache=surface_translation_cache,
            )
            for match, senses, key, form_is_inflected in group_inputs
        }

    translations: dict[tuple[str, str], str | None] = {}
    with ThreadPoolExecutor(max_workers=min(4, len(group_inputs))) as executor:
        futures = {
            executor.submit(
                _initial_group_translation,
                match=match,
                senses=senses,
                form_is_inflected=form_is_inflected,
                en_gemini_translation_service=en_gemini_translation_service,
                translation_service=translation_service,
                translation_cache=translation_cache,
                surface_translation_cache=surface_translation_cache,
            ): key
            for match, senses, key, form_is_inflected in group_inputs
        }
        for future in as_completed(futures):
            key = futures[future]
            translations[key] = future.result()
    return translations


def _initial_group_translation(
    *,
    match,
    senses,
    form_is_inflected: bool,
    en_gemini_translation_service,
    translation_service: TranslationService | None,
    translation_cache: dict[tuple[str, str, str], str | None],
    surface_translation_cache: dict[str, str | None],
) -> str | None:
    if form_is_inflected:
        group_translation = _translate_en_surface_form(
            form=match.form,
            translation_service=translation_service,
            cache=surface_translation_cache,
        )
        if not group_translation:
            group_translation = translate_en_lemma_contextual(
                lemma=match.lemma,
                pos_ud=match.pos_ud,
                gloss=senses[0].gloss,
                gemini_service=en_gemini_translation_service,
                translation_service=translation_service,
                cache=translation_cache,
            )
    else:
        group_translation = translate_en_lemma_contextual(
            lemma=match.lemma,
            pos_ud=match.pos_ud,
            gloss=senses[0].gloss,
            gemini_service=en_gemini_translation_service,
            translation_service=translation_service,
            cache=translation_cache,
        )
        if not group_translation:
            group_translation = _translate_en_surface_form(
                form=match.form,
                translation_service=translation_service,
                cache=surface_translation_cache,
            )
    group_translation = _normalize_translation_candidate(group_translation)
    if group_translation and group_translation.lower() == match.lemma.lower():
        return None
    return group_translation


def _initial_group_translations_batched(
    *,
    normalized_query: str,
    group_inputs: list[tuple[object, list[object], tuple[str, str], bool]],
    en_gemini_translation_service,
) -> dict[tuple[str, str], str | None] | None:
    batch_translate = getattr(en_gemini_translation_service, "translate_english_lemmas_batch", None)
    if not callable(batch_translate):
        return None
    candidates = [
        {
            "id": str(index),
            "lemma": match.lemma,
            "pos_ud": match.pos_ud,
            "gloss": senses[0].gloss,
        }
        for index, (match, senses, _key, _form_is_inflected) in enumerate(group_inputs)
    ]
    try:
        results = batch_translate(query=normalized_query, candidates=candidates)
    except Exception:
        return None
    translations: dict[tuple[str, str], str | None] = {}
    for index, (match, _senses, key, _form_is_inflected) in enumerate(group_inputs):
        value = _normalize_translation_candidate(results.get(str(index)))
        if value and value.lower() == match.lemma.lower():
            value = None
        translations[key] = value
    return translations


def _flag_enabled(name: str, *, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no"}


def _attach_disambiguation_descriptions(
    *,
    normalized_query: str,
    groups: list[ENPosGroup],
    en_gemini_translation_service,
) -> None:
    if en_gemini_translation_service is None:
        return
    translated_groups = [group for group in groups if group.danish_translation]
    if len(translated_groups) < 2:
        return
    describer = getattr(en_gemini_translation_service, "describe_translation_choices", None)
    if not callable(describer):
        return
    choices = [
        {
            "id": str(index),
            "english_lemma": group.lemma,
            "english_query": normalized_query,
            "pos_ud": group.pos_ud,
            "danish_translation": group.danish_translation,
            "glosses": [sense.gloss for sense in group.senses[:3] if sense.gloss],
            "examples": [example for sense in group.senses[:2] for example in sense.examples[:1] if example],
        }
        for index, group in enumerate(translated_groups)
    ]
    try:
        descriptions = describer(query=normalized_query, choices=choices)
    except Exception:
        return
    if not isinstance(descriptions, dict):
        return
    for choice, group in zip(choices, translated_groups, strict=False):
        description = descriptions.get(choice["id"])
        if isinstance(description, str):
            normalized = " ".join(description.strip().split())
            group.meaning_description = normalized or None
