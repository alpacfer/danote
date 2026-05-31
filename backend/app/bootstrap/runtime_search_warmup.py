from __future__ import annotations

import logging

from fastapi import FastAPI

from app.core.app_state import get_runtime_state, set_runtime_field
from app.core.config import Settings

logger = logging.getLogger(__name__)

# These match common COR translation frames and stay within one provider batch.
SEARCH_WARMUP_TEXTS = (
    "en bog",
    "et hus",
    "at være",
    "at have",
    "at spise",
    "en god ting",
    "han gør det godt",
    "i huset",
)


def initialize_search_warmup(app: FastAPI, settings: Settings) -> None:
    set_runtime_field(app, "search_warmup_completed", False)
    set_runtime_field(app, "search_warmup_error", None)
    if not settings.search_warmup_enabled:
        return

    translation = get_runtime_state(app).services.translation_service
    if translation is None:
        return

    try:
        translation.translate_da_to_en_batch(list(SEARCH_WARMUP_TEXTS))
        gemini = get_runtime_state(app).services.gemini_word_translation_service
        warmup_gemini = getattr(gemini, "warmup", None)
        if callable(warmup_gemini):
            warmup_gemini()
    except Exception as exc:
        logger.warning(
            "backend_search_warmup_failed",
            extra={
                "provider": getattr(translation, "provider", None),
                "operation": "startup.search_warmup",
                "failure_class": exc.__class__.__name__,
                "retryable": True,
            },
            exc_info=exc,
        )
        set_runtime_field(app, "search_warmup_error", "Failed to warm the translation provider.")
        return

    set_runtime_field(app, "search_warmup_completed", True)
    logger.info(
        "backend_search_warmup_completed",
        extra={
            "provider": getattr(translation, "provider", None),
            "text_count": len(SEARCH_WARMUP_TEXTS),
            "gemini_request_count": 0,
            "gemini_client_initialized": callable(warmup_gemini),
        },
    )
