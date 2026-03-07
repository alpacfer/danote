from __future__ import annotations

import logging

from fastapi import FastAPI

from app.bootstrap.runtime_translation import RuntimeApiKeyOverrides
from app.core.app_state import get_runtime_state, set_runtime_field, set_service_field
from app.core.config import Settings
from app.services.verification import GeminiWordVerificationService

logger = logging.getLogger(__name__)


def initialize_word_verification(
    app: FastAPI,
    settings: Settings,
    overrides: RuntimeApiKeyOverrides | None = None,
) -> None:
    set_runtime_field(app, "word_verification_error", None)
    _close_service(get_runtime_state(app).services.word_verification_service)
    set_service_field(app, "word_verification_service", None)
    if not settings.word_verification_enabled:
        return

    verification_key = _override_or_setting(
        overrides,
        "word_verification_gemini",
        settings.word_verification_gemini_api_key,
    )
    if verification_key:
        try:
            set_service_field(
                app,
                "word_verification_service",
                GeminiWordVerificationService(
                    api_key=verification_key,
                    model=settings.word_verification_gemini_model,
                ),
            )
        except Exception:
            logger.exception("backend_word_verification_startup_failed")
            set_runtime_field(
                app,
                "word_verification_error",
                "Failed to initialize Gemini word verification service.",
            )
    else:
        logger.warning("backend_word_verification_startup_skipped_missing_gemini_key")
        set_runtime_field(
            app,
            "word_verification_error",
            "Missing DANOTE_WORD_VERIFICATION_GEMINI_API_KEY.",
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
