from __future__ import annotations

from typing import Literal

from app.api.schemas.v1.sentencebank import (
    SentenceSearchPreviewResponse,
    SentenceVerificationErrorItem,
    VerifySentenceResponse,
)
from app.services.sentence_verification import (
    SentenceVerificationResult,
    SentenceVerificationService,
)
from app.services.translation import TranslationService
from app.services.use_cases.sentencebank_text import (
    heuristic_detect_language,
    normalize_query_language,
    normalize_sentence_text_without_terminal_period,
    preserve_leading_letter_case,
)
from app.services.use_cases.wordbank import WordbankUseCase


def build_verify_sentence_response(
    *,
    normalized_text: str,
    sentence_verification_service: SentenceVerificationService | None,
) -> VerifySentenceResponse:
    if sentence_verification_service is None:
        return VerifySentenceResponse(is_valid=True, errors=[], corrected_text=None, language="unknown")
    result = sentence_verification_service.verify_sentence(normalized_text)
    return VerifySentenceResponse(
        is_valid=result.is_valid,
        errors=[
            SentenceVerificationErrorItem(start=error.start, end=error.end, message=error.message)
            for error in result.errors
        ],
        corrected_text=result.corrected_text,
        language=result.language,
    )


def build_sentence_search_preview(
    *,
    normalized_query: str,
    translation_service: TranslationService | None,
    wordbank_use_case: WordbankUseCase | None,
    sentence_verification_service: SentenceVerificationService | None,
    fast: bool,
) -> SentenceSearchPreviewResponse:
    if fast:
        return build_sentence_search_preview_fast(
            normalized_query=normalized_query,
            translation_service=translation_service,
            wordbank_use_case=wordbank_use_case,
        )

    initial_verification = verify_sentence_result(
        source_text=normalized_query,
        sentence_verification_service=sentence_verification_service,
    )
    query_language = initial_verification.language
    if query_language == "unknown":
        query_language = detect_query_language(
            source_text=normalized_query,
            translation_service=translation_service,
        )

    if query_language == "en":
        english_for_translation = (
            preserve_leading_letter_case(normalized_query, initial_verification.corrected_text)
            or normalized_query
        )
        translated_danish = lookup_reverse_translation(
            source_text=english_for_translation,
            translation_service=translation_service,
        )
        if not translated_danish:
            return SentenceSearchPreviewResponse(
                status="blocked",
                query_language="en",
                source_text=None,
                english_translation=None,
                is_valid=False,
                errors=[],
                message="Could not translate this English sentence to Danish.",
            )
        return SentenceSearchPreviewResponse(
            status="ready",
            query_language="en",
            source_text=translated_danish,
            english_translation=english_for_translation,
            is_valid=True,
            errors=[],
            message=None,
        )

    final_source_text = initial_verification.corrected_text or normalized_query
    return SentenceSearchPreviewResponse(
        status="ready",
        query_language=query_language,
        source_text=final_source_text,
        english_translation=lookup_phrase_translation(
            source_text=final_source_text,
            translation_service=translation_service,
            wordbank_use_case=wordbank_use_case,
        ),
        is_valid=initial_verification.is_valid,
        errors=[
            SentenceVerificationErrorItem(start=error.start, end=error.end, message=error.message)
            for error in initial_verification.errors
        ],
        message=None,
    )


def build_sentence_search_preview_fast(
    *,
    normalized_query: str,
    translation_service: TranslationService | None,
    wordbank_use_case: WordbankUseCase | None,
) -> SentenceSearchPreviewResponse:
    query_language = detect_query_language(
        source_text=normalized_query,
        translation_service=translation_service,
    )
    if query_language == "unknown":
        query_language = heuristic_detect_language(normalized_query)
    if query_language == "en":
        translated_danish = lookup_reverse_translation(
            source_text=normalized_query,
            translation_service=translation_service,
        )
        if not translated_danish:
            return SentenceSearchPreviewResponse(
                status="blocked",
                query_language="en",
                source_text=None,
                english_translation=None,
                is_valid=True,
                errors=[],
                message=None,
            )
        return SentenceSearchPreviewResponse(
            status="preview",
            query_language="en",
            source_text=translated_danish,
            english_translation=normalized_query,
            is_valid=True,
            errors=[],
            message=None,
        )

    effective_language: Literal["da", "en", "unknown"] = "da" if query_language == "da" else "unknown"
    return SentenceSearchPreviewResponse(
        status="preview",
        query_language=effective_language,
        source_text=normalized_query,
        english_translation=lookup_phrase_translation(
            source_text=normalized_query,
            translation_service=translation_service,
            wordbank_use_case=wordbank_use_case,
        ),
        is_valid=True,
        errors=[],
        message=None,
    )


def lookup_phrase_translation(
    *,
    source_text: str,
    translation_service: TranslationService | None,
    wordbank_use_case: WordbankUseCase | None,
) -> str | None:
    if wordbank_use_case is not None:
        try:
            payload = wordbank_use_case.generate_phrase_translation(source_text)
            if payload.english_translation:
                return preserve_leading_letter_case(source_text, payload.english_translation)
        except Exception:
            pass
    if translation_service is None:
        return None
    try:
        translated = translation_service.translate_da_to_en(source_text)
        if not isinstance(translated, str):
            return None
        cleaned = " ".join(translated.strip().split()) or None
        return preserve_leading_letter_case(source_text, cleaned)
    except Exception:
        return None


def lookup_reverse_translation(
    *,
    source_text: str,
    translation_service: TranslationService | None,
) -> str | None:
    if translation_service is None:
        return None
    translate_en_to_da = getattr(translation_service, "translate_en_to_da", None)
    if not callable(translate_en_to_da):
        return None
    try:
        translated = translate_en_to_da(source_text)
        return (
            normalize_sentence_text_without_terminal_period(translated)
            if isinstance(translated, str) and translated.strip()
            else None
        )
    except Exception:
        return None


def detect_query_language(
    *,
    source_text: str,
    translation_service: TranslationService | None,
) -> Literal["da", "en", "unknown"]:
    if translation_service is None:
        return "unknown"
    detect_source_language = getattr(translation_service, "detect_source_language", None)
    if not callable(detect_source_language):
        return "unknown"
    try:
        return normalize_query_language(detect_source_language(source_text))
    except Exception:
        return "unknown"


def verify_sentence_result(
    *,
    source_text: str,
    sentence_verification_service: SentenceVerificationService | None,
) -> SentenceVerificationResult:
    if sentence_verification_service is None:
        return SentenceVerificationResult(
            is_valid=True,
            errors=[],
            corrected_text=None,
            language="unknown",
        )
    try:
        return sentence_verification_service.verify_sentence(source_text)
    except Exception:
        return SentenceVerificationResult(
            is_valid=True,
            errors=[],
            corrected_text=None,
            language="unknown",
        )


def translation_provider_name(translation_service: TranslationService | None) -> str:
    provider = getattr(translation_service, "provider", None)
    if isinstance(provider, str):
        cleaned = provider.strip().lower()
        if cleaned:
            return cleaned
    return "translation"
