from __future__ import annotations

import logging

from fastapi import FastAPI

from app.bootstrap.runtime_translation import RuntimeApiKeyOverrides
from app.core.app_state import get_runtime_state, set_runtime_field, set_service_field
from app.core.config import Settings
from app.services.related_words import GeminiCompoundRelatedWordsService, RelatedWordsError

logger = logging.getLogger(__name__)


def initialize_related_words(
    app: FastAPI,
    settings: Settings,
    overrides: RuntimeApiKeyOverrides | None = None,
) -> None:
    set_runtime_field(app, "related_words_error", None)
    _close_service(get_runtime_state(app).services.gemini_related_words_service)
    set_service_field(app, "gemini_related_words_service", None)

    related_words_key = _override_or_setting(
        overrides,
        "gemini_api_key",
        settings.gemini_api_key,
    )
    if not related_words_key:
        logger.warning("backend_related_words_startup_skipped_missing_gemini_key")
        set_runtime_field(app, "related_words_error", "Missing DANOTE_GEMINI_API_KEY.")
        return

    try:
        set_service_field(
            app,
            "gemini_related_words_service",
            GeminiCompoundRelatedWordsService(
                api_key=related_words_key,
                model=settings.gemini_model,
            ),
        )
    except (RelatedWordsError, ValueError, TypeError) as exc:
        logger.warning("backend_related_words_startup_failed", exc_info=exc)
        set_runtime_field(app, "related_words_error", "Failed to initialize Gemini related words service.")


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
