from __future__ import annotations

import logging

from app.core.config import Settings
from app.services.deepl_translation import DeepLTranslationService
from app.services.en_gemini_translation import (
    ENGeminiTranslationError,
    ENGeminiTranslationService,
)
from app.services.gemini_result_cache import GeminiResultCache
from app.services.gemini_translation import (
    GeminiFlashLiteWordTranslationService,
    GeminiTranslationError,
)
from app.services.related_words import GeminiCompoundRelatedWordsService, RelatedWordsError
from app.services.sentence_verification import GeminiSentenceVerificationService
from app.services.translation import AzureTranslationService, TranslationError
from app.services.tts import AzureSpeechTTSService
from app.services.verification import GeminiWordVerificationService

logger = logging.getLogger(__name__)


def build_translation_service(*, settings: Settings, api_key: str) -> object | None:
    """Build a translation service for a user-supplied key, matching the host's selected provider."""
    provider = settings.translation_provider.strip().lower()
    if provider == "azure":
        if not settings.translation_azure_region:
            return None
        try:
            return AzureTranslationService(
                api_key=api_key,
                region=settings.translation_azure_region,
                endpoint=settings.translation_azure_endpoint,
                api_version=settings.translation_azure_api_version,
            )
        except (TranslationError, ValueError, TypeError) as exc:
            logger.warning("user_key_build_failed", extra={"provider": "azure_translation", "error": str(exc)})
            return None
    if provider == "deepl":
        try:
            return DeepLTranslationService(
                api_key=api_key,
                endpoint=settings.translation_deepl_endpoint,
            )
        except (TranslationError, ValueError, TypeError) as exc:
            logger.warning("user_key_build_failed", extra={"provider": "deepl", "error": str(exc)})
            return None
    return None


def build_gemini_word_translation_service(*, settings: Settings, api_key: str) -> object | None:
    try:
        cache = (
            GeminiResultCache(settings.search_gemini_cache_path)
            if settings.search_gemini_cache_enabled
            else None
        )
        return GeminiFlashLiteWordTranslationService(
            api_key=api_key,
            model=settings.gemini_model,
            cache=cache,
        )
    except (GeminiTranslationError, ValueError, TypeError) as exc:
        logger.warning("user_key_build_failed", extra={"provider": "gemini_word_translation", "error": str(exc)})
        return None


def build_gemini_related_words_service(*, settings: Settings, api_key: str) -> object | None:
    try:
        return GeminiCompoundRelatedWordsService(
            api_key=api_key,
            model=settings.gemini_model,
        )
    except (RelatedWordsError, ValueError, TypeError) as exc:
        logger.warning("user_key_build_failed", extra={"provider": "gemini_related_words", "error": str(exc)})
        return None


def build_en_gemini_translation_service(*, settings: Settings, api_key: str) -> object | None:
    try:
        cache = (
            GeminiResultCache(settings.search_gemini_cache_path)
            if settings.search_gemini_cache_enabled
            else None
        )
        return ENGeminiTranslationService(
            api_key=api_key,
            model=settings.gemini_model,
            cache=cache,
        )
    except (ENGeminiTranslationError, ValueError, TypeError) as exc:
        logger.warning("user_key_build_failed", extra={"provider": "en_gemini_translation", "error": str(exc)})
        return None


def build_word_verification_service(*, settings: Settings, api_key: str) -> object | None:
    if not settings.word_verification_enabled:
        return None
    try:
        return GeminiWordVerificationService(
            api_key=api_key,
            model=settings.word_verification_gemini_model or settings.gemini_model,
        )
    except (ValueError, TypeError) as exc:
        logger.warning("user_key_build_failed", extra={"provider": "word_verification", "error": str(exc)})
        return None


def build_sentence_verification_service(*, settings: Settings, api_key: str) -> object | None:
    using_word_verification_settings = bool(settings.word_verification_gemini_api_key)
    model = (
        settings.word_verification_gemini_model
        if using_word_verification_settings
        else settings.gemini_model
    )
    try:
        return GeminiSentenceVerificationService(
            api_key=api_key,
            model=model,
        )
    except (ValueError, TypeError) as exc:
        logger.warning("user_key_build_failed", extra={"provider": "sentence_verification", "error": str(exc)})
        return None


def build_tts_service(*, settings: Settings, api_key: str) -> object | None:
    if not settings.tts_enabled:
        return None
    provider = settings.tts_provider.strip().lower()
    if provider != "azure":
        return None
    if not settings.tts_azure_region:
        return None
    try:
        return AzureSpeechTTSService(
            api_key=api_key,
            region=settings.tts_azure_region,
            endpoint=settings.tts_azure_endpoint,
            voice_name=settings.tts_azure_voice_name,
        )
    except (ValueError, TypeError) as exc:
        logger.warning("user_key_build_failed", extra={"provider": "azure_tts", "error": str(exc)})
        return None
