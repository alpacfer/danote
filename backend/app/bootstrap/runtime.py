from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.bootstrap.runtime_cor import initialize_cor, initialize_cor_local
from app.bootstrap.runtime_db import initialize_database
from app.bootstrap.runtime_gemini_word_translation import initialize_gemini_word_translation
from app.bootstrap.runtime_nlp import initialize_nlp
from app.bootstrap.runtime_related_words import initialize_related_words
from app.bootstrap.runtime_sentence_verification import initialize_sentence_verification
from app.bootstrap.runtime_steps import StartupStep, run_startup_step
from app.bootstrap.runtime_translation import initialize_translation
from app.bootstrap.runtime_tts import initialize_tts
from app.bootstrap.runtime_word_verification import initialize_word_verification
from app.bootstrap.runtime_wordbank_background_jobs import initialize_wordbank_background_jobs
from app.core.app_state import close_runtime_services, get_runtime_state
from app.core.config import Settings
from app.nlp.adapter import NLPAdapter

logger = logging.getLogger(__name__)


def default_nlp_adapter_factory(settings: Settings) -> NLPAdapter:
    # Import lazily so missing NLP dependencies degrade health instead of crashing import.
    from app.nlp.danish import load_danish_nlp_adapter

    return load_danish_nlp_adapter(settings)


def startup_lifespan(
    settings: Settings,
    nlp_adapter_factory: Callable[[Settings], NLPAdapter],
):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        applied = initialize_runtime(app, settings, nlp_adapter_factory)
        log_startup(app, applied)
        yield
        close_runtime_services(app)

    return lifespan


def initialize_runtime(
    app: FastAPI,
    settings: Settings,
    nlp_adapter_factory: Callable[[Settings], NLPAdapter],
) -> list[str]:
    applied = initialize_database(app, settings)
    for step in build_startup_steps(nlp_adapter_factory):
        run_startup_step(step, app, settings)
    if get_runtime_state(app).db_ready:
        initialize_wordbank_background_jobs(app, settings)
    return applied


def build_startup_steps(
    nlp_adapter_factory: Callable[[Settings], NLPAdapter],
) -> tuple[StartupStep, ...]:
    return (
        StartupStep("nlp", lambda app, settings: initialize_nlp(app, settings, nlp_adapter_factory)),
        StartupStep("cor_local", initialize_cor_local),
        StartupStep("cor", initialize_cor),
        StartupStep("translation", initialize_translation),
        StartupStep("gemini_word_translation", initialize_gemini_word_translation),
        StartupStep("related_words", initialize_related_words),
        StartupStep("word_verification", initialize_word_verification),
        StartupStep("sentence_verification", initialize_sentence_verification),
        StartupStep("tts", initialize_tts),
    )


def log_startup(app: FastAPI, applied: list[str]) -> None:
    runtime = get_runtime_state(app)
    settings = runtime.settings
    services = runtime.services
    nlp_requirement_met = (not settings.nlp_enabled) or runtime.nlp_ready
    startup_status = "ok" if runtime.db_ready and nlp_requirement_met else "degraded"
    logger.info(
        "backend_startup",
        extra={
            "status": startup_status,
            "environment": settings.environment,
            "db_path": str(settings.db_path),
            "host": settings.host,
            "port": settings.port,
            "applied_migrations": applied,
            "db_error": runtime.db_error,
            "nlp_error": runtime.nlp_error,
            "nlp": services.nlp_adapter.metadata() if services.nlp_adapter else None,
            "translation_enabled": settings.translation_enabled,
            "translation_error": runtime.translation_error,
            "translation_provider": (
                getattr(services.translation_service, "provider", None)
                if services.translation_service
                else None
            ),
            "gemini_word_translation_error": runtime.gemini_word_translation_error,
            "gemini_word_translation_provider": (
                getattr(services.gemini_word_translation_service, "provider", None)
                if services.gemini_word_translation_service
                else None
            ),
            "related_words_error": runtime.related_words_error,
            "related_words_provider": (
                getattr(services.gemini_related_words_service, "provider", None)
                if services.gemini_related_words_service
                else None
            ),
            "word_verification_enabled": settings.word_verification_enabled,
            "word_verification_error": runtime.word_verification_error,
            "word_verification_provider": (
                getattr(services.word_verification_service, "provider", None)
                if services.word_verification_service
                else None
            ),
            "tts_enabled": settings.tts_enabled,
            "tts_error": runtime.tts_error,
            "tts_provider": getattr(services.tts_service, "provider", None) if services.tts_service else None,
            "tts_model": getattr(services.tts_service, "model", None) if services.tts_service else None,
            "cor_lookup_enabled": settings.cor_lookup_enabled,
            "cor_lookup_error": runtime.cor_lookup_error,
            "cor_local_db_path": str(settings.cor_local_db_path),
            "cor_local_lookup_error": runtime.cor_local_lookup_error,
        },
    )
