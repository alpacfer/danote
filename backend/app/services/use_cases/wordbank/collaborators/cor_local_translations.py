from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from app.services.cor_local import CORLocalEntry
from app.services.gemini_translation import ContextualWordTranslationInput
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.collaborators.translation_word_frames import (
    WordTranslationFrame,
    cor_local_word_translation_frame,
)
from app.services.use_cases.wordbank.collaborators.translation import TranslationCollaborator
from app.services.use_cases.wordbank.collaborators.translation_search_fallbacks import (
    SearchTranslationDecision,
    build_search_translation_decision,
    evaluate_search_translation_candidate,
    invalid_search_translation,
)

logger = logging.getLogger(__name__)

ContextualCacheKey = tuple[str, str, str | None, str | None, str | None, str | None, str | None]
WordFrameCacheKey = WordTranslationFrame
AzureFrameCacheKey = WordFrameCacheKey


@dataclass(frozen=True, slots=True)
class _BatchContextualRequest:
    payload: ContextualWordTranslationInput
    cache_key: ContextualCacheKey


def lookup_translation_for_cor_gloss(
    translation: TranslationCollaborator,
    *,
    entry: CORLocalEntry,
    lemma_translation: str | None = None,
    cache: dict[ContextualCacheKey, str | None] | None = None,
    strict_azure: bool = False,
    gloss_cache: dict[str, str | None] | None = None,
) -> str | None:
    normalized_gloss = normalize_token(entry.gloss or "")
    if not normalized_gloss:
        return None
    if strict_azure:
        _require_azure_translation(translation)
        lookup_translation = translation.lookup_translation_strict
    else:
        if translation._translation_service is None:
            return None
        lookup_translation = translation.lookup_translation
    fallback_cache_key = (
        entry.form,
        entry.lemma,
        entry.pos_tag,
        entry.morphology,
        normalized_gloss,
        lemma_translation,
        None,
    )
    if cache is not None and fallback_cache_key in cache and cache[fallback_cache_key] is not None:
        return cache[fallback_cache_key]

    def _lookup(text: str) -> str | None:
        if gloss_cache is not None and text in gloss_cache:
            return gloss_cache[text]
        return lookup_translation(text)

    translated = _lookup(normalized_gloss)
    if translated and translated != normalized_gloss:
        if cache is not None:
            cache[fallback_cache_key] = translated
        return translated

    parts = [normalize_token(part) for part in normalized_gloss.split(",")]
    parts = [part for part in parts if part]
    if len(parts) > 1:
        translated_parts: list[str] = []
        for part in parts:
            part_translated = _lookup(part)
            translated_parts.append(part_translated or part)
        merged = ", ".join(translated_parts)
        if cache is not None:
            cache[fallback_cache_key] = merged
        return merged

    if cache is not None:
        cache[fallback_cache_key] = translated
    return translated


def lookup_translation_for_cor_local_entry(
    translation: TranslationCollaborator,
    entry: CORLocalEntry,
    cache: dict[AzureFrameCacheKey, str | None] | None = None,
    contextual_cache: dict[ContextualCacheKey, str | None] | None = None,
    gloss_cache: dict[str, str | None] | None = None,
    strict_azure: bool = False,
) -> str | None:
    return search_translation_decision_for_cor_local_entry(
        translation,
        entry,
        cache=cache,
        contextual_cache=contextual_cache,
        gloss_cache=gloss_cache,
        strict_azure=strict_azure,
    ).lemma_translation


def search_translation_decision_for_cor_local_entry(
    translation: TranslationCollaborator,
    entry: CORLocalEntry,
    cache: dict[AzureFrameCacheKey, str | None] | None = None,
    contextual_cache: dict[ContextualCacheKey, str | None] | None = None,
    gloss_cache: dict[str, str | None] | None = None,
    strict_azure: bool = False,
) -> SearchTranslationDecision:
    if strict_azure:
        _require_azure_translation(translation)
        lookup_translation = translation.lookup_translation_strict
    else:
        lookup_translation = translation.lookup_translation
    frame = cor_local_word_translation_frame(entry)
    if cache is not None and frame in cache:
        cleaned_translation = cache[frame]
    else:
        translated = lookup_translation(frame.text)
        cleaned_translation = translation.cleanup_framed_word_translation(frame, translated)
        if cache is not None:
            cache[frame] = cleaned_translation
    provider_formatted = _format_lemma_translation(entry, cleaned_translation)
    normalized_gloss = normalize_token(entry.gloss or "")
    gloss_translation_hint = (
        gloss_cache.get(normalized_gloss)
        if gloss_cache is not None and normalized_gloss
        else None
    )
    contextual_attempted = False
    contextual_formatted: str | None = None
    if _should_use_gemini_for_lemma(
        entry,
        frame=frame,
        provider_translation=cleaned_translation,
    ):
        contextual_attempted = True
        contextual = translation.lookup_contextual_word_translation(
            surface_form=entry.form,
            lemma=entry.lemma,
            pos_tag=entry.pos_tag,
            morphology=entry.morphology,
            gloss=normalized_gloss,
            gloss_translation_hint=gloss_translation_hint,
            cache=contextual_cache,
        )
        if contextual.translation:
            contextual_formatted = _format_lemma_translation(entry, contextual.translation)

    provider_candidate = evaluate_search_translation_candidate(
        translation=provider_formatted,
        lemma=entry.lemma,
        surface_form=entry.form,
        frame_text=frame.text,
    )
    contextual_candidate = (
        evaluate_search_translation_candidate(
            translation=contextual_formatted,
            lemma=entry.lemma,
            surface_form=entry.form,
            frame_text=frame.text,
        )
        if contextual_attempted
        else None
    )
    decision = build_search_translation_decision(
        provider_candidate=provider_candidate,
        provider_name=translation.provider_name(),
        contextual_candidate=contextual_candidate,
        contextual_provider_name=translation.contextual_provider_name(),
        contextual_attempted=contextual_attempted,
        gloss_fallback=gloss_translation_hint,
    )
    _log_rejected_search_translation(
        entry,
        frame=frame,
        provider=translation.provider_name(),
        rejection_reason="provider_self_translation",
        candidate=provider_candidate,
    )
    if (
        contextual_attempted
        and contextual_candidate is not None
        and contextual_candidate.invalid is not None
        and decision.lemma_translation_status != "gemini"
    ):
        _log_rejected_search_translation(
            entry,
            frame=frame,
            provider=translation.contextual_provider_name(),
            rejection_reason="gemini_self_translation",
            candidate=contextual_candidate,
        )
    if decision.lemma_translation_status == "gloss_fallback":
        _log_gloss_fallback(
            entry,
            gloss_translation_hint=gloss_translation_hint,
            provider=translation.provider_name(),
        )
    return decision


def lemma_translation_for_entry(
    translation: TranslationCollaborator,
    entry: CORLocalEntry,
    cache: dict[AzureFrameCacheKey, str | None],
    contextual_cache: dict[ContextualCacheKey, str | None],
) -> str | None:
    return search_translation_decision_for_cor_local_entry(
        translation,
        entry,
        cache=cache,
        contextual_cache=contextual_cache,
        strict_azure=False,
    ).lemma_translation


def prime_cor_form_contextual_translations(
    translation: TranslationCollaborator,
    entries: list[CORLocalEntry],
    *,
    cache: dict[ContextualCacheKey, str | None],
    lemma_cache: dict[AzureFrameCacheKey, str | None] | None = None,
    gloss_cache: dict[str, str | None] | None = None,
) -> None:
    _require_azure_translation(translation)
    if lemma_cache is None:
        lemma_cache = {}
    if gloss_cache is None:
        gloss_cache = {}
    _prime_azure_lemma_translations(translation, entries, lemma_cache, gloss_cache)
    requests_by_key = _collect_gemini_batch_requests(
        entries,
        translation,
        cache,
        lemma_cache,
        gloss_cache,
    )
    if not requests_by_key:
        return
    _run_gemini_batch(translation, list(requests_by_key.values()), cache)


def _prime_azure_lemma_translations(
    translation: TranslationCollaborator,
    entries: list[CORLocalEntry],
    lemma_cache: dict[WordFrameCacheKey, str | None],
    gloss_cache: dict[str, str | None],
) -> None:
    unique_texts: list[str] = []
    text_seen: set[str] = set(gloss_cache)
    text_seen.update(frame.text for frame in lemma_cache)
    missing_frames: list[WordTranslationFrame] = []
    for entry in entries:
        frame = cor_local_word_translation_frame(entry)
        if frame not in lemma_cache:
            missing_frames.append(frame)
            if frame.text not in text_seen:
                unique_texts.append(frame.text)
                text_seen.add(frame.text)
        normalized_gloss = normalize_token(entry.gloss or "")
        if normalized_gloss:
            for text in _gloss_translation_texts(normalized_gloss):
                if text not in text_seen:
                    unique_texts.append(text)
                    text_seen.add(text)
    if not unique_texts:
        return
    batch_results = translation.lookup_translation_batch_strict(unique_texts)
    for frame in missing_frames:
        if frame not in lemma_cache:
            lemma_cache[frame] = translation.cleanup_framed_word_translation(
                frame,
                batch_results.get(frame.text),
            )
    for text in _gloss_translation_texts_from_entries(entries):
        if text not in batch_results:
            continue
        gloss_cache[text] = batch_results[text]


def _collect_gemini_batch_requests(
    entries: list[CORLocalEntry],
    translation: TranslationCollaborator,
    cache: dict[ContextualCacheKey, str | None],
    lemma_cache: dict[WordFrameCacheKey, str | None],
    gloss_cache: dict[str, str | None],
) -> dict[ContextualCacheKey, _BatchContextualRequest]:
    requests_by_key: dict[ContextualCacheKey, _BatchContextualRequest] = {}
    for entry in entries:
        frame = cor_local_word_translation_frame(entry)
        cleaned_translation = lemma_cache.get(frame)
        if not _should_use_gemini_for_lemma(
            entry,
            frame=frame,
            provider_translation=cleaned_translation,
        ):
            continue
        request = _build_contextual_request(
            translation,
            entry,
            gloss_translation_hint=gloss_cache.get(normalize_token(entry.gloss or "")),
        )
        if request is None or request.cache_key in cache or request.cache_key in requests_by_key:
            continue
        requests_by_key[request.cache_key] = request
    return requests_by_key


def _run_gemini_batch(
    translation: TranslationCollaborator,
    requests: list[_BatchContextualRequest],
    cache: dict[ContextualCacheKey, str | None],
) -> None:
    started_at = time.perf_counter()
    batch_results = translation.batch_lookup_contextual_word_translations(
        [request.payload for request in requests],
        cache=cache,
    )
    unresolved_count = sum(
        1
        for request, result in zip(requests, batch_results, strict=False)
        if result.translation is None and cache.get(request.cache_key) is None
    )

    logger.info(
        "wordbank_cor_form_batch_translations",
        extra={
            "batch_size": len(requests),
            "batch_latency_seconds": round(time.perf_counter() - started_at, 4),
            "unresolved_count": unresolved_count,
        },
    )


def _gloss_translation_texts(normalized_gloss: str) -> list[str]:
    texts = [normalized_gloss]
    parts = [normalize_token(part) for part in normalized_gloss.split(",")]
    parts = [p for p in parts if p]
    if len(parts) > 1:
        texts.extend(parts)
    return texts


def _gloss_translation_texts_from_entries(entries: list[CORLocalEntry]) -> list[str]:
    texts: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        normalized_gloss = normalize_token(entry.gloss or "")
        if not normalized_gloss:
            continue
        for text in _gloss_translation_texts(normalized_gloss):
            if text in seen:
                continue
            seen.add(text)
            texts.append(text)
    return texts


def _build_contextual_request(
    translation: TranslationCollaborator,
    entry: CORLocalEntry,
    *,
    gloss_translation_hint: str | None = None,
) -> _BatchContextualRequest | None:
    payload = ContextualWordTranslationInput(
        surface_form=entry.form,
        lemma=entry.lemma,
        pos_tag=entry.pos_tag,
        morphology=entry.morphology,
        gloss=normalize_token(entry.gloss or "") or None,
        gloss_translation_hint=normalize_token(gloss_translation_hint or "") or None,
    )
    if not payload.surface_form or not payload.lemma:
        return None
    return _BatchContextualRequest(
        payload=payload,
        cache_key=translation.contextual_translation_cache_key(payload),
    )


def _should_use_gemini_for_lemma(
    entry: CORLocalEntry,
    *,
    frame: WordTranslationFrame,
    provider_translation: str | None,
) -> bool:
    normalized_gloss = normalize_token(entry.gloss or "")
    if normalized_gloss:
        return True
    # If cleanup yielded nothing, the provider gave us no usable result; try
    # Gemini for a contextual translation rather than silently returning None.
    if provider_translation is None:
        return True
    invalid = invalid_search_translation(
        translation=provider_translation,
        lemma=entry.lemma,
        surface_form=entry.form,
        frame_text=frame.text,
    )
    return invalid is not None


def _format_lemma_translation(entry: CORLocalEntry, translated: str | None) -> str | None:
    normalized = normalize_token(translated or "")
    if not normalized:
        return None
    if entry.pos_tag != "VERB":
        return normalized
    if normalized.startswith("to "):
        return normalized
    return f"to {normalized}"


def _log_rejected_search_translation(
    entry: CORLocalEntry,
    *,
    frame: WordTranslationFrame,
    provider: str,
    rejection_reason: str,
    candidate,
) -> None:
    invalid = candidate.invalid
    if invalid is None:
        return
    logger.info(
        "wordbank_search_translation_rejected",
        extra={
            "provider": provider,
            "rejection_reason": rejection_reason,
            "matched_source": invalid.matched_source,
            "comparable_value": invalid.comparable_value,
            "lemma": entry.lemma,
            "surface_form": entry.form,
            "frame_text": frame.text,
            "translation": normalize_token(candidate.translation or "") or None,
        },
    )


def _log_gloss_fallback(
    entry: CORLocalEntry,
    *,
    gloss_translation_hint: str | None,
    provider: str,
) -> None:
    normalized_gloss_fallback = normalize_token(gloss_translation_hint or "") or None
    if not normalized_gloss_fallback:
        return
    logger.info(
        "wordbank_search_translation_gloss_fallback",
        extra={
            "provider": provider,
            "lemma": entry.lemma,
            "surface_form": entry.form,
            "gloss_translation": normalized_gloss_fallback,
        },
    )


def _require_azure_translation(translation: TranslationCollaborator) -> None:
    if translation._translation_service is None:
        raise RuntimeError("Azure translation is unavailable.")
