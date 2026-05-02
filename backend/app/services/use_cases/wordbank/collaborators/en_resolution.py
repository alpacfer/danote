from __future__ import annotations

from collections import OrderedDict

from app.api.schemas.v1.wordbank import (
    ENPosGroup,
    ENSearchFormResponse,
    ENSenseOut,
    ResolveQueryResponse,
)
from app.services.en_local import ENLocalLexiconService
from app.services.translation import TranslationService
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

    for match in sorted_matches:
        key = (match.lemma.lower(), match.pos_ud)
        if key in groups_by_key:
            continue
        senses = en_local_lexicon_service.lookup_lemma_senses(match.lemma, match.pos_ud)
        if not senses:
            continue
        senses = senses[:_MAX_SENSES_PER_POS]
        sense_outs: list[ENSenseOut] = []
        group_translation = _translate_en_surface_form(
            form=match.form,
            translation_service=translation_service,
            cache=surface_translation_cache,
        ) if include_translations else None
        for sense in senses:
            translation_value = group_translation
            if include_translations:
                if not translation_value:
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
            "examples": [
                example
                for sense in group.senses[:2]
                for example in sense.examples[:1]
                if example
            ],
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
