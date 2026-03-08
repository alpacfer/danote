from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from app.services.cor_local import CORLocalEntry
from app.services.gemini_translation import ContextualWordTranslationInput
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.collaborators.cor_azure_frames import (
    CORAzureFrame,
    azure_framed_translation_for_comparison,
    cor_local_azure_frame,
)
from app.services.use_cases.wordbank.collaborators.translation import TranslationCollaborator

logger = logging.getLogger(__name__)

ContextualCacheKey = tuple[str, str, str | None, str | None, str | None, str | None, str | None]
AzureFrameCacheKey = CORAzureFrame


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
    if strict_azure:
        _require_azure_translation(translation)
        lookup_translation = translation.lookup_translation_strict
    else:
        lookup_translation = translation.lookup_translation
    frame = cor_local_azure_frame(entry)
    if cache is not None and frame in cache:
        translated = cache[frame]
    else:
        translated = lookup_translation(frame.text)
        if cache is not None:
            cache[frame] = translated
    azure_for_comparison = azure_framed_translation_for_comparison(frame, translated)
    normalized_gloss = normalize_token(entry.gloss or "")
    gloss_translation_hint = (
        gloss_cache.get(normalized_gloss)
        if gloss_cache is not None and normalized_gloss
        else None
    )
    if _should_use_gemini_for_lemma(
        entry,
        frame=frame,
        azure_translation=azure_for_comparison,
    ):
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
            return _resolve_contextual_lemma_translation(
                entry,
                contextual_translation=contextual_formatted,
                gloss_translation_hint=gloss_translation_hint,
            )
    return _format_lemma_translation(entry, azure_for_comparison)


def lemma_translation_for_entry(
    translation: TranslationCollaborator,
    entry: CORLocalEntry,
    cache: dict[AzureFrameCacheKey, str | None],
    contextual_cache: dict[ContextualCacheKey, str | None],
) -> str | None:
    return lookup_translation_for_cor_local_entry(
        translation,
        entry,
        cache,
        contextual_cache,
        strict_azure=False,
    )


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
    lemma_cache: dict[AzureFrameCacheKey, str | None],
    gloss_cache: dict[str, str | None],
) -> None:
    unique_texts: list[str] = []
    text_seen: set[str] = set(gloss_cache)
    text_seen.update(frame.text for frame in lemma_cache)
    missing_frames: list[CORAzureFrame] = []
    for entry in entries:
        frame = cor_local_azure_frame(entry)
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
            lemma_cache[frame] = batch_results.get(frame.text)
    for text in _gloss_translation_texts_from_entries(entries):
        if text not in batch_results:
            continue
        gloss_cache[text] = batch_results[text]


def _collect_gemini_batch_requests(
    entries: list[CORLocalEntry],
    translation: TranslationCollaborator,
    cache: dict[ContextualCacheKey, str | None],
    lemma_cache: dict[AzureFrameCacheKey, str | None],
    gloss_cache: dict[str, str | None],
) -> dict[ContextualCacheKey, _BatchContextualRequest]:
    requests_by_key: dict[ContextualCacheKey, _BatchContextualRequest] = {}
    for entry in entries:
        frame = cor_local_azure_frame(entry)
        translated = lemma_cache.get(frame)
        azure_for_comparison = azure_framed_translation_for_comparison(frame, translated)
        if not _should_use_gemini_for_lemma(
            entry,
            frame=frame,
            azure_translation=azure_for_comparison,
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
    frame: CORAzureFrame,
    azure_translation: str | None,
) -> bool:
    normalized_gloss = normalize_token(entry.gloss or "")
    if normalized_gloss:
        return True
    normalized_lemma = normalize_token(entry.lemma)
    normalized_frame = normalize_token(frame.text)
    normalized_translation = normalize_token(azure_translation or "")
    if (
        entry.pos_tag == "VERB"
        and normalized_lemma
        and normalized_translation == f"to {normalized_lemma}"
    ):
        return True
    return bool(
        (normalized_lemma and normalized_translation and normalized_lemma == normalized_translation)
        or (
            normalized_frame
            and normalized_translation
            and normalized_frame == normalized_translation
        )
    )


def _format_lemma_translation(entry: CORLocalEntry, translated: str | None) -> str | None:
    normalized = normalize_token(translated or "")
    if not normalized:
        return None
    if entry.pos_tag != "VERB":
        return normalized
    if normalized.startswith("to "):
        return normalized
    return f"to {normalized}"


def _resolve_contextual_lemma_translation(
    entry: CORLocalEntry,
    *,
    contextual_translation: str | None,
    gloss_translation_hint: str | None,
) -> str | None:
    normalized_contextual = normalize_token(contextual_translation or "")
    if not normalized_contextual:
        return None
    normalized_lemma = normalize_token(entry.lemma)
    normalized_hint = normalize_token(gloss_translation_hint or "")
    if (
        entry.pos_tag != "VERB"
        and normalized_lemma
        and normalized_hint
        and normalized_contextual == normalized_lemma
        and normalized_hint != normalized_lemma
    ):
        return normalized_hint
    return normalized_contextual


def _require_azure_translation(translation: TranslationCollaborator) -> None:
    if translation._translation_service is None:
        raise RuntimeError("Azure translation is unavailable.")
