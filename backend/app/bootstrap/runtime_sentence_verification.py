from __future__ import annotations

import logging

from fastapi import FastAPI

from app.core.app_state import get_runtime_state, set_runtime_field, set_service_field
from app.core.config import Settings
from app.services.sentence_verification import GeminiSentenceVerificationService

logger = logging.getLogger(__name__)


def initialize_sentence_verification(
    app: FastAPI,
    settings: Settings,
) -> None:
    set_runtime_field(app, "sentence_verification_error", None)
    _close_service(get_runtime_state(app).services.sentence_verification_service)
    set_service_field(app, "sentence_verification_service", None)

    gemini_key = settings.gemini_api_key
    if gemini_key:
        try:
            set_service_field(
                app,
                "sentence_verification_service",
                GeminiSentenceVerificationService(
                    api_key=gemini_key,
                    model=settings.gemini_model,
                ),
            )
            logger.info("backend_sentence_verification_startup_ok")
        except Exception:
            logger.exception("backend_sentence_verification_startup_failed")
            set_runtime_field(
                app,
                "sentence_verification_error",
                "Failed to initialize Gemini sentence verification service.",
            )
    else:
        logger.warning("backend_sentence_verification_startup_skipped_missing_gemini_key")
        set_runtime_field(
            app,
            "sentence_verification_error",
            "Missing DANOTE_GEMINI_API_KEY.",
        )


def _close_service(service: object | None) -> None:
    close = getattr(service, "close", None)
    if callable(close):
        close()
