from __future__ import annotations

import logging

from fastapi import FastAPI

from app.bootstrap.runtime_translation import RuntimeApiKeyOverrides
from app.core.app_state import (
    get_runtime_state,
    set_runtime_field,
    set_service_field,
)
from app.core.config import Settings
from app.services.en_gemini_translation import (
    ENGeminiTranslationError,
    ENGeminiTranslationService,
)
from app.services.gemini_result_cache import GeminiResultCache

logger = logging.getLogger(__name__)


def initialize_en_gemini_translation(
    app: FastAPI,
    settings: Settings,
    overrides: RuntimeApiKeyOverrides | None = None,
) -> None:
    set_runtime_field(app, "en_gemini_translation_error", None)
    _close_service(get_runtime_state(app).services.en_gemini_translation_service)
    set_service_field(app, "en_gemini_translation_service", None)

    gemini_key = _override_or_setting(
        overrides,
        "gemini_api_key",
        settings.gemini_api_key,
    )
    if not gemini_key:
        set_runtime_field(
            app,
            "en_gemini_translation_error",
            "Missing DANOTE_GEMINI_API_KEY.",
        )
        return

    try:
        cache = GeminiResultCache(settings.search_gemini_cache_path) if settings.search_gemini_cache_enabled else None
        set_service_field(
            app,
            "en_gemini_translation_service",
            ENGeminiTranslationService(
                api_key=gemini_key,
                model=settings.gemini_model,
                cache=cache,
            ),
        )
    except (ENGeminiTranslationError, ValueError, TypeError) as exc:
        logger.warning(
            "backend_en_gemini_translation_startup_failed",
            extra={
                "provider": "en_gemini_translation",
                "operation": "startup.initialize",
                "failure_class": exc.__class__.__name__,
            },
            exc_info=exc,
        )
        set_runtime_field(
            app,
            "en_gemini_translation_error",
            "Failed to initialize Gemini EN→DA translation service.",
        )


def _override_or_setting(
    overrides: RuntimeApiKeyOverrides | None,
    field_name: str,
    setting_value: str | None,
) -> str | None:
    if overrides and field_name in overrides and overrides[field_name]:
        return overrides[field_name]
    return setting_value


def _close_service(service: object | None) -> None:
    close = getattr(service, "close", None)
    if callable(close):
        close()
