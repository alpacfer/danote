from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from app.services.cor_local import CORLocalEntry
from app.services.gemini_translation import ContextualWordTranslationInput
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.collaborators.cor_local_translations import (
    lookup_translation_for_cor_local_entry,
)
from app.services.use_cases.wordbank.collaborators.translation import TranslationLookupResult
from app.services.use_cases.wordbank.commands_add_word_models import AddWordCommandInputs
from app.services.use_cases.wordbank.meaning_sections import MeaningResolution
from app.services.use_cases.wordbank.runtime import WordbankRuntime


@dataclass(frozen=True, slots=True)
class _ContextualTranslationTarget:
    id: Literal["lemma"]
    surface_form: str
    lemma: str
    preferred_pos_tag: str | None
    preferred_morphology: str | None
    cor_entry: CORLocalEntry | None


@dataclass(frozen=True, slots=True)
class TranslationSelection:
    lemma: TranslationLookupResult


NO_TRANSLATION = TranslationLookupResult(translation=None, provider=None)
_LIKELY_ENGLISH_GLOSS_RE = re.compile(r"^[A-Za-z][A-Za-z ',-]*$")


def lookup_word_translations(
    runtime: WordbankRuntime,
    inputs: AddWordCommandInputs,
    meaning_resolution: MeaningResolution | None,
) -> TranslationSelection:
    lemma_cor_entry = None
    prefer_cor_lemma_translation = False
    preferred_pos_tag = inputs.selected_pos_tag
    preferred_morphology = inputs.selected_morphology
    if meaning_resolution is not None:
        lemma_cor_entry = meaning_resolution.lemma_cor_entry or meaning_resolution.surface_cor_entry
        prefer_cor_lemma_translation = meaning_resolution.lemma_cor_entry is not None or (
            meaning_resolution.surface_cor_entry is not None
            and normalize_token(meaning_resolution.surface_cor_entry.form) == inputs.stored_lemma
        )
        preferred_pos_tag = meaning_resolution.pos_tag
        preferred_morphology = meaning_resolution.morphology
    elif inputs.normalized_cor_id:
        surface_cor_entry = runtime.cor.cor_local_entry_for_cor_id(cor_id=inputs.normalized_cor_id)
        if surface_cor_entry is not None and normalize_token(surface_cor_entry.lemma) == inputs.stored_lemma:
            lemma_cor_entry = runtime.cor.best_cor_local_lemma_entry(
                lemma_idx=surface_cor_entry.lemma_idx,
                lemma=inputs.stored_lemma,
                preferred_pos_tag=surface_cor_entry.pos_tag or inputs.selected_pos_tag,
            )
            prefer_cor_lemma_translation = lemma_cor_entry is not None
            preferred_pos_tag = surface_cor_entry.pos_tag or inputs.selected_pos_tag
            preferred_morphology = surface_cor_entry.morphology or inputs.selected_morphology

    targets = [
        _ContextualTranslationTarget(
            id="lemma",
            surface_form=inputs.stored_lemma,
            lemma=inputs.stored_lemma,
            preferred_pos_tag=preferred_pos_tag,
            preferred_morphology=preferred_morphology,
            cor_entry=lemma_cor_entry,
        )
    ]
    contextual_results = _batch_lookup_contextual_translations(runtime, targets)
    resolved: dict[str, TranslationLookupResult] = {}
    for target in targets:
        if target.id == "lemma" and prefer_cor_lemma_translation and lemma_cor_entry is not None:
            resolved[target.id] = _resolve_cor_lemma_translation(runtime, cor_entry=lemma_cor_entry)
            continue
        contextual = contextual_results.get(target.id, NO_TRANSLATION)
        resolved[target.id] = _resolve_translation_with_fallback(runtime, target, contextual)

    return TranslationSelection(lemma=resolved.get("lemma", NO_TRANSLATION))


def _batch_lookup_contextual_translations(
    runtime: WordbankRuntime,
    targets: list[_ContextualTranslationTarget],
) -> dict[str, TranslationLookupResult]:
    if not targets:
        return {}

    payloads_by_key: dict[
        tuple[str, str, str | None, str | None, str | None, str | None, str | None, str | None],
        ContextualWordTranslationInput,
    ] = {}
    target_key_by_id: dict[str, tuple[str, str, str | None, str | None, str | None, str | None, str | None, str | None]] = {}
    for target in targets:
        payload = _build_contextual_payload(runtime, target)
        cache_key = runtime.translation.contextual_translation_cache_key(payload)
        target_key_by_id[target.id] = cache_key
        if cache_key not in payloads_by_key:
            payloads_by_key[cache_key] = payload

    contextual_results = runtime.translation.batch_lookup_contextual_word_translations(
        list(payloads_by_key.values())
    )
    result_by_key = {
        key: result
        for key, result in zip(payloads_by_key.keys(), contextual_results, strict=False)
    }
    return {
        target_id: result_by_key.get(cache_key, NO_TRANSLATION)
        for target_id, cache_key in target_key_by_id.items()
    }


def _build_contextual_payload(
    runtime: WordbankRuntime,
    target: _ContextualTranslationTarget,
) -> ContextualWordTranslationInput:
    cor_entry = target.cor_entry
    if cor_entry is None:
        cor_entry = runtime.cor.best_cor_local_entry_for_form(
            form=target.surface_form,
            lemma=target.lemma,
            preferred_pos_tag=target.preferred_pos_tag,
        )
    if cor_entry is None:
        return ContextualWordTranslationInput(
            surface_form=target.surface_form,
            lemma=target.lemma,
            pos_tag=target.preferred_pos_tag,
            morphology=target.preferred_morphology,
            gloss=None,
        )
    return ContextualWordTranslationInput(
        surface_form=target.surface_form,
        lemma=target.lemma,
        pos_tag=target.preferred_pos_tag or cor_entry.pos_tag,
        morphology=target.preferred_morphology or cor_entry.morphology,
        gloss=normalize_token(cor_entry.gloss or "") or None,
    )


def _resolve_translation_with_fallback(
    runtime: WordbankRuntime,
    target: _ContextualTranslationTarget,
    contextual: TranslationLookupResult,
) -> TranslationLookupResult:
    if contextual.translation:
        return contextual

    translated = runtime.translation.lookup_translation(target.surface_form)
    if (
        translated
        and " " not in target.surface_form
        and runtime.translation.normalize_comparable(translated)
        == runtime.translation.normalize_comparable(target.surface_form)
    ):
        return NO_TRANSLATION
    return TranslationLookupResult(
        translation=translated,
        provider=runtime.translation.provider_name() if translated else None,
    )


def _resolve_cor_lemma_translation(
    runtime: WordbankRuntime,
    *,
    cor_entry: CORLocalEntry,
) -> TranslationLookupResult:
    frame = runtime.translation.build_word_translation_frame(
        lemma=cor_entry.lemma,
        pos_tag=cor_entry.pos_tag,
        gram_or_function=cor_entry.gram_raw,
        morphology=cor_entry.morphology,
    )
    framed_translation = runtime.translation.lookup_framed_word_translation(frame).translation
    if framed_translation and _is_likely_english_gloss(cor_entry.gloss):
        return TranslationLookupResult(
            translation=framed_translation,
            provider=runtime.translation.provider_name(),
        )

    translated = lookup_translation_for_cor_local_entry(runtime.translation, cor_entry)
    return TranslationLookupResult(
        translation=translated,
        provider=runtime.translation.provider_name() if translated else None,
    )


def _is_likely_english_gloss(gloss: str | None) -> bool:
    normalized_gloss = normalize_token(gloss or "")
    if not normalized_gloss:
        return False
    return _LIKELY_ENGLISH_GLOSS_RE.fullmatch(normalized_gloss) is not None
