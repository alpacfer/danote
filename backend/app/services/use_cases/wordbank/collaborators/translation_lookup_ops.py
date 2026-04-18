from __future__ import annotations

import httpx

from app.services.gemini_translation import GeminiTranslationError
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.collaborators.translation_models import TranslationLookupResult
from app.services.use_cases.wordbank.collaborators.translation_contextual import (
    build_contextual_input,
)
from app.services.use_cases.wordbank.collaborators.translation_failures import (
    ProviderFailureReason,
)
from app.services.use_cases.wordbank.collaborators.translation_helpers import (
    best_cor_local_entry,
    best_cor_local_entry_with_gloss,
    contextual_provider_name,
    log_provider_failure,
    normalize_comparable,
    normalize_translation_value,
    provider_name,
)
from app.services.use_cases.wordbank.collaborators.translation_word_frames import (
    cor_local_word_translation_frame,
)


def lookup_word_translation(collaborator, source_word: str, lemma: str | None = None) -> TranslationLookupResult:
    normalized_source = normalize_token(source_word)
    normalized_lemma = normalize_token(lemma or "") or normalized_source
    contextual = lookup_contextual_word_translation(
        collaborator,
        surface_form=normalized_source,
        lemma=normalized_lemma,
    )
    if contextual.translation:
        return contextual

    cor_entry = best_cor_local_entry(
        collaborator._cor_local_lexicon_service,
        form=normalized_source,
        lemma=normalized_lemma,
        preferred_pos_tag=None,
    )
    if cor_entry is not None:
        framed_translation = collaborator.lookup_framed_word_translation(
            cor_local_word_translation_frame(cor_entry)
        )
        if framed_translation.translation:
            if (
                " " not in normalized_source
                and normalize_comparable(framed_translation.translation)
                == normalize_comparable(normalized_source)
            ):
                return TranslationLookupResult(translation=None, provider=None)
            return framed_translation

    translated = collaborator.lookup_translation(normalized_source)
    if (
        translated
        and " " not in normalized_source
        and normalize_comparable(translated) == normalize_comparable(normalized_source)
    ):
        return TranslationLookupResult(translation=None, provider=None)
    return TranslationLookupResult(
        translation=translated,
        provider=provider_name(collaborator._translation_service) if translated else None,
    )


def lookup_contextual_word_translation(
    collaborator,
    *,
    surface_form: str,
    lemma: str,
    pos_tag: str | None = None,
    morphology: str | None = None,
    gloss: str | None = None,
    lemma_translation_hint: str | None = None,
    gloss_translation_hint: str | None = None,
    cache: dict[tuple[str, str, str | None, str | None, str, str | None, str | None], str | None] | None = None,
) -> TranslationLookupResult:
    normalized_surface = normalize_token(surface_form)
    normalized_lemma = normalize_token(lemma)
    normalized_gloss = normalize_token(gloss or "")
    if not normalized_surface or not normalized_lemma:
        return TranslationLookupResult(translation=None, provider=None)

    context_entry = build_contextual_input(
        surface_form=normalized_surface,
        lemma=normalized_lemma,
        pos_tag=pos_tag,
        morphology=morphology,
        gloss=normalized_gloss,
        lemma_translation_hint=lemma_translation_hint,
        gloss_translation_hint=gloss_translation_hint,
        best_cor_local_entry_with_gloss=lambda **kwargs: best_cor_local_entry_with_gloss(
            collaborator._cor_local_lexicon_service,
            **kwargs,
        ),
    )

    if collaborator._gemini_word_translation_service is None:
        return TranslationLookupResult(translation=None, provider=None)

    cache_key = (
        context_entry.surface_form,
        context_entry.lemma,
        context_entry.pos_tag,
        context_entry.morphology,
        context_entry.gloss,
        context_entry.lemma_translation_hint,
        context_entry.gloss_translation_hint,
    )
    if cache is not None and cache_key in cache:
        return TranslationLookupResult(
            translation=cache[cache_key],
            provider=contextual_provider_name(collaborator._gemini_word_translation_service),
        )

    try:
        translated = collaborator._gemini_word_translation_service.translate_word(context_entry)
        normalized = normalize_translation_value(translated)
    except (GeminiTranslationError, httpx.HTTPError, TimeoutError, ValueError, TypeError) as exc:
        log_provider_failure(
            logger=collaborator._logger,
            provider=contextual_provider_name(collaborator._gemini_word_translation_service),
            operation="translate_word",
            reason=ProviderFailureReason.PROVIDER,
            retryable=False,
            exc=exc,
        )
        normalized = None

    if cache is not None:
        cache[cache_key] = normalized
    return TranslationLookupResult(
        translation=normalized,
        provider=contextual_provider_name(collaborator._gemini_word_translation_service),
    )


def batch_lookup_contextual_word_translations(
    collaborator,
    payloads,
    *,
    cache: dict[tuple[str, str, str | None, str | None, str | None, str | None, str | None], str | None]
    | None = None,
) -> list[TranslationLookupResult]:
    if not payloads:
        return []
    if collaborator._gemini_word_translation_service is None:
        return [TranslationLookupResult(translation=None, provider=None) for _ in payloads]

    try:
        translated = collaborator._gemini_word_translation_service.translate_words_batch(payloads)
    except (GeminiTranslationError, httpx.HTTPError, TimeoutError, ValueError, TypeError) as exc:
        log_provider_failure(
            logger=collaborator._logger,
            provider=contextual_provider_name(collaborator._gemini_word_translation_service),
            operation="translate_words_batch",
            reason=ProviderFailureReason.PROVIDER,
            retryable=False,
            exc=exc,
        )
        translated = [None] * len(payloads)

    results: list[TranslationLookupResult] = []
    for index, payload in enumerate(payloads):
        value = translated[index] if index < len(translated) else None
        normalized = normalize_translation_value(value)
        if cache is not None:
            cache[collaborator.contextual_translation_cache_key(payload)] = normalized
        results.append(
            TranslationLookupResult(
                translation=normalized,
                provider=contextual_provider_name(collaborator._gemini_word_translation_service),
            )
        )

    return results


def lookup_contextual_word_translation_from_payload(
    collaborator,
    payload,
    *,
    cache: dict[tuple[str, str, str | None, str | None, str | None, str | None, str | None], str | None]
    | None = None,
) -> TranslationLookupResult:
    if collaborator._gemini_word_translation_service is None:
        return TranslationLookupResult(translation=None, provider=None)
    cache_key = collaborator.contextual_translation_cache_key(payload)
    if cache is not None and cache_key in cache:
        return TranslationLookupResult(
            translation=cache[cache_key],
            provider=contextual_provider_name(collaborator._gemini_word_translation_service),
        )
    try:
        translated = collaborator._gemini_word_translation_service.translate_word(payload)
        normalized = normalize_translation_value(translated)
    except (GeminiTranslationError, httpx.HTTPError, TimeoutError, ValueError, TypeError) as exc:
        log_provider_failure(
            logger=collaborator._logger,
            provider=contextual_provider_name(collaborator._gemini_word_translation_service),
            operation="translate_word",
            reason=ProviderFailureReason.PROVIDER,
            retryable=False,
            exc=exc,
        )
        normalized = None
    if cache is not None:
        cache[cache_key] = normalized
    return TranslationLookupResult(
        translation=normalized,
        provider=contextual_provider_name(collaborator._gemini_word_translation_service),
    )
