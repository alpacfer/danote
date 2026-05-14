from __future__ import annotations

from collections.abc import Callable

import httpx

from app.api.schemas.v1.wordbank import (
    DetectWordLanguageResponse,
    GeneratePhraseTranslationResponse,
    GenerateReverseTranslationResponse,
)
from app.db.migrations import get_connection
from app.services.translation import TranslationError
from app.services.use_cases.wordbank.collaborators.translation_failures import (
    ProviderCallResult,
    ProviderFailureReason,
)
from app.services.use_cases.wordbank.collaborators.translation_helpers import (
    log_provider_failure,
    normalize_translation_value,
    not_configured_result,
    provider_failure_result,
    provider_name,
)
from app.services.use_cases.wordbank.collaborators.translation_language_detection import (
    detect_word_language as detect_word_language_with_fallbacks,
)
from app.services.use_cases.wordbank.collaborators.translation_helpers import provider_name as fallback_provider_name
from app.services.use_cases.wordbank.collaborators.translation_sentence_text import (
    align_sentence_translation_capitalization,
    normalize_sentence_text,
    normalize_sentence_translation_value,
)
from app.services.token_classifier import normalize_token


def generate_phrase_translation(collaborator, source_text: str) -> GeneratePhraseTranslationResponse:
    normalized_source_text = normalize_token(source_text)
    display_source_text = normalize_sentence_text(source_text)
    if not normalized_source_text or not display_source_text:
        raise ValueError("source_text is required")

    with get_connection(collaborator._db_path) as conn:
        existing = conn.execute(
            """
            SELECT english_translation
            FROM phrase_translations
            WHERE owner_user_id = ? AND source_phrase = ?
            LIMIT 1
            """,
            (collaborator._owner_user_id, normalized_source_text),
        ).fetchone()

        if existing is not None:
            cached_translation = align_sentence_translation_capitalization(
                display_source_text,
                normalize_sentence_translation_value(existing["english_translation"]),
            )
            return GeneratePhraseTranslationResponse(
                status="cached" if cached_translation else "unavailable",
                source_text=display_source_text,
                english_translation=cached_translation,
            )

        english_translation = align_sentence_translation_capitalization(
            display_source_text,
            lookup_phrase_translation(collaborator, display_source_text),
        )
        provider = fallback_provider_name(collaborator._translation_service)
        conn.execute(
            """
            INSERT INTO phrase_translations (
                owner_user_id,
                source_phrase,
                english_translation,
                translation_provider
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                collaborator._owner_user_id,
                normalized_source_text,
                english_translation,
                provider if english_translation else None,
            ),
        )

    return GeneratePhraseTranslationResponse(
        status="generated" if english_translation else "unavailable",
        source_text=display_source_text,
        english_translation=english_translation,
    )


def generate_reverse_translation(collaborator, source_word: str) -> GenerateReverseTranslationResponse:
    normalized_source = normalize_token(source_word)
    if not normalized_source:
        raise ValueError("source_word is required")
    danish_translation_raw = lookup_reverse_translation_result(collaborator, normalized_source).value
    danish_translation = normalize_token(danish_translation_raw) if danish_translation_raw else None
    return GenerateReverseTranslationResponse(
        status="generated" if danish_translation else "unavailable",
        source_word=normalized_source,
        danish_translation=danish_translation,
    )


def detect_word_language(
    collaborator,
    source_word: str,
    *,
    cor_entries_lookup: Callable[[str], list] | None = None,
) -> DetectWordLanguageResponse:
    return detect_word_language_with_fallbacks(
        source_word,
        detect_source_language=collaborator._lookup_detected_source_language,
        cor_entries_lookup=cor_entries_lookup,
    )


def lookup_phrase_translation(collaborator, source_text: str) -> str | None:
    if collaborator._translation_service is None:
        return None
    try:
        translated = collaborator._translation_service.translate_da_to_en(source_text)
        if translated is None:
            normalized_source_text = normalize_token(source_text)
            if normalized_source_text and normalized_source_text != source_text:
                translated = collaborator._translation_service.translate_da_to_en(normalized_source_text)
        return normalize_sentence_translation_value(translated)
    except (TranslationError, httpx.TimeoutException, TimeoutError) as exc:
        log_provider_failure(
            logger=collaborator._logger,
            provider=provider_name(collaborator._translation_service),
            operation="translate_da_to_en",
            reason=ProviderFailureReason.TIMEOUT,
            retryable=True,
            exc=exc,
        )
        return None
    except (httpx.HTTPStatusError, PermissionError) as exc:
        log_provider_failure(
            logger=collaborator._logger,
            provider=provider_name(collaborator._translation_service),
            operation="translate_da_to_en",
            reason=ProviderFailureReason.HTTP,
            retryable=False,
            exc=exc,
        )
        return None
    except Exception as exc:
        log_provider_failure(
            logger=collaborator._logger,
            provider=provider_name(collaborator._translation_service),
            operation="translate_da_to_en",
            reason=ProviderFailureReason.UNKNOWN,
            retryable=False,
            exc=exc,
        )
        return None


def lookup_reverse_translation_result(collaborator, source_word: str) -> ProviderCallResult:
    if collaborator._translation_service is None:
        return not_configured_result(
            provider=provider_name(collaborator._translation_service),
            operation="translate_en_to_da",
        )
    translate_en_to_da = getattr(collaborator._translation_service, "translate_en_to_da", None)
    if not callable(translate_en_to_da):
        return not_configured_result(
            provider=provider_name(collaborator._translation_service),
            operation="translate_en_to_da",
        )
    try:
        translated = translate_en_to_da(source_word)
        return ProviderCallResult(value=normalize_translation_value(translated))
    except (TranslationError, httpx.TimeoutException, TimeoutError) as exc:
        return provider_failure_result(
            logger=collaborator._logger,
            provider=provider_name(collaborator._translation_service),
            operation="translate_en_to_da",
            reason=ProviderFailureReason.TIMEOUT,
            retryable=True,
            exc=exc,
        )
    except (httpx.HTTPStatusError, PermissionError) as exc:
        return provider_failure_result(
            logger=collaborator._logger,
            provider=provider_name(collaborator._translation_service),
            operation="translate_en_to_da",
            reason=ProviderFailureReason.AUTH,
            retryable=False,
            exc=exc,
        )
    except (httpx.HTTPError, ConnectionError, RuntimeError) as exc:
        return provider_failure_result(
            logger=collaborator._logger,
            provider=provider_name(collaborator._translation_service),
            operation="translate_en_to_da",
            reason=ProviderFailureReason.PROVIDER,
            retryable=True,
            exc=exc,
        )


def lookup_detected_source_language_result(collaborator, source_word: str) -> ProviderCallResult:
    if collaborator._translation_service is None:
        return not_configured_result(
            provider=provider_name(collaborator._translation_service),
            operation="detect_source_language",
        )
    detect_source_language = getattr(collaborator._translation_service, "detect_source_language", None)
    if not callable(detect_source_language):
        return not_configured_result(
            provider=provider_name(collaborator._translation_service),
            operation="detect_source_language",
        )
    try:
        provider_language = detect_source_language(source_word)
    except (TranslationError, httpx.TimeoutException, TimeoutError) as exc:
        return provider_failure_result(
            logger=collaborator._logger,
            provider=provider_name(collaborator._translation_service),
            operation="detect_source_language",
            reason=ProviderFailureReason.TIMEOUT,
            retryable=True,
            exc=exc,
        )
    except (httpx.HTTPStatusError, PermissionError) as exc:
        return provider_failure_result(
            logger=collaborator._logger,
            provider=provider_name(collaborator._translation_service),
            operation="detect_source_language",
            reason=ProviderFailureReason.AUTH,
            retryable=False,
            exc=exc,
        )
    except (httpx.HTTPError, ConnectionError, ValueError, TypeError, RuntimeError) as exc:
        return provider_failure_result(
            logger=collaborator._logger,
            provider=provider_name(collaborator._translation_service),
            operation="detect_source_language",
            reason=ProviderFailureReason.PARSE,
            retryable=False,
            exc=exc,
        )
    if not provider_language:
        return ProviderCallResult(value=None)
    normalized = provider_language.strip().lower()
    if normalized.startswith("en"):
        return ProviderCallResult(value="en")
    if normalized.startswith("da"):
        return ProviderCallResult(value="da")
    return ProviderCallResult(value=None)
