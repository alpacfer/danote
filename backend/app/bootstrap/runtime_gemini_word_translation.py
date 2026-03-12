from __future__ import annotations

import logging

from fastapi import FastAPI

from app.bootstrap.runtime_translation import RuntimeApiKeyOverrides
from app.core.app_state import get_runtime_state, set_runtime_field, set_service_field
from app.core.config import Settings
from app.services.gemini_translation import GeminiFlashLiteWordTranslationService, GeminiTranslationError

logger = logging.getLogger(__name__)


def _log_startup_failure(*, exc: Exception) -> None:
    logger.warning(
        "backend_gemini_word_translation_startup_failed",
        extra={
            "provider": "gemini_word_translation",
            "operation": "startup.initialize",
            "failure_class": exc.__class__.__name__,
            "retryable": False,
        },
        exc_info=exc,
    )


def initialize_gemini_word_translation(
    app: FastAPI,
    settings: Settings,
    overrides: RuntimeApiKeyOverrides | None = None,
) -> None:
    set_runtime_field(app, "gemini_word_translation_error", None)
    _close_service(get_runtime_state(app).services.gemini_word_translation_service)
    set_service_field(app, "gemini_word_translation_service", None)

    gemini_key = _override_or_setting(
        overrides,
        "gemini_api_key",
        settings.gemini_api_key,
    )
    if gemini_key:
        try:
            set_service_field(
                app,
                "gemini_word_translation_service",
                GeminiFlashLiteWordTranslationService(
                    api_key=gemini_key,
                    model=settings.gemini_model,
                ),
            )
        except (GeminiTranslationError, ValueError, TypeError) as exc:
            _log_startup_failure(exc=exc)
            set_runtime_field(
                app,
                "gemini_word_translation_error",
                "Failed to initialize Gemini word translation service.",
            )
    else:
        logger.warning("backend_gemini_word_translation_startup_skipped_missing_gemini_key")
        set_runtime_field(
            app,
            "gemini_word_translation_error",
            "Missing DANOTE_GEMINI_API_KEY.",
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
