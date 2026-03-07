from __future__ import annotations

import logging
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app.core.app_state import (
    close_runtime_services,
    get_runtime_state,
    set_runtime_field,
    set_service_field,
)
from app.core.config import Settings
from app.db.migrations import apply_migrations
from app.nlp.adapter import NLPAdapter
from app.services.cor import CORLexiconService
from app.services.cor_local import CORLocalLexiconService
from app.services.translation import AzureTranslationService
from app.services.tts import AzureSpeechTTSService
from app.services.typo.typo_engine import TypoEngine
from app.services.verification import GeminiWordVerificationService

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
    applied = _init_db(app, settings)
    _init_nlp(app, settings, nlp_adapter_factory)
    _init_cor_local(app, settings)
    _init_cor(app, settings)
    _init_typo(app, settings)
    _init_translation(app, settings)
    _init_word_verification(app, settings)
    _init_tts(app, settings)
    return applied


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
            "typo_enabled": bool(services.typo_engine is not None),
            "translation_enabled": settings.translation_enabled,
            "translation_error": runtime.translation_error,
            "translation_provider": (
                getattr(services.translation_service, "provider", None)
                if services.translation_service
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


def log_timed_startup_step(step: str, operation: Callable[[], None]) -> None:
    started_at = time.perf_counter()
    operation()
    logger.info(
        "backend_startup_step_completed",
        extra={"step": step, "duration_ms": round((time.perf_counter() - started_at) * 1000, 2)},
    )


def _init_db(app: FastAPI, settings: Settings) -> list[str]:
    applied: list[str] = []

    def operation() -> None:
        nonlocal applied
        try:
            settings.db_path.parent.mkdir(parents=True, exist_ok=True)
            applied = apply_migrations(settings.db_path)
            set_runtime_field(app, "db_ready", True)
            set_runtime_field(app, "db_error", None)
        except Exception as exc:
            set_runtime_field(app, "db_ready", False)
            set_runtime_field(app, "db_error", str(exc))
            logger.exception("backend_db_startup_failed", extra={"db_path": str(settings.db_path)})

    log_timed_startup_step("database", operation)
    return applied


def _init_nlp(app: FastAPI, settings: Settings, factory: Callable[[Settings], NLPAdapter]) -> None:
    def operation() -> None:
        set_runtime_field(app, "nlp_error", None)
        adapter: NLPAdapter | None = None
        if settings.nlp_enabled:
            try:
                adapter = factory(settings)
                set_runtime_field(app, "nlp_ready", True)
            except Exception as exc:
                set_runtime_field(app, "nlp_ready", False)
                set_runtime_field(app, "nlp_error", str(exc))
                logger.exception("backend_nlp_startup_failed", extra={"nlp_model": settings.nlp_model})
        else:
            set_runtime_field(app, "nlp_ready", False)
        set_service_field(app, "nlp_adapter", adapter)

    log_timed_startup_step("nlp", operation)


def _init_cor_local(app: FastAPI, settings: Settings) -> None:
    def operation() -> None:
        set_service_field(
            app,
            "cor_local_lexicon_service",
            CORLocalLexiconService(db_path=settings.cor_local_db_path),
        )
        set_runtime_field(app, "cor_local_lookup_error", None)

    log_timed_startup_step("cor_local", operation)


def _init_cor(app: FastAPI, settings: Settings) -> None:
    def operation() -> None:
        set_service_field(app, "cor_lexicon_service", None)
        set_runtime_field(app, "cor_lookup_error", None)
        if settings.cor_lookup_enabled:
            try:
                set_service_field(
                    app,
                    "cor_lexicon_service",
                    CORLexiconService(timeout_seconds=settings.cor_lookup_timeout_seconds),
                )
            except Exception:
                logger.exception("backend_cor_lookup_startup_failed")
                set_runtime_field(app, "cor_lookup_error", "Failed to initialize COR lookup service.")

    log_timed_startup_step("cor", operation)


def _init_typo(app: FastAPI, settings: Settings) -> None:
    def operation() -> None:
        runtime = get_runtime_state(app)
        typo_engine = None
        if settings.typo_enabled and runtime.db_ready:
            resources_path = Path(__file__).resolve().parents[2] / "resources" / "dictionaries"
            configured_dictionary_path = settings.typo_dictionary_path
            dictionary_paths = tuple(
                path
                for path in dict.fromkeys(
                    (
                        resources_path / "da_words.txt",
                        resources_path / "dsdo.txt",
                        configured_dictionary_path,
                    )
                )
                if path is not None
            )
            try:
                typo_engine = TypoEngine(
                    db_path=settings.db_path,
                    dictionary_paths=dictionary_paths,
                )
            except Exception:
                logger.exception("backend_typo_engine_startup_failed")
        set_service_field(app, "typo_engine", typo_engine)

    log_timed_startup_step("typo", operation)


def _init_translation(app: FastAPI, settings: Settings) -> None:
    def operation() -> None:
        set_runtime_field(app, "translation_error", None)
        set_service_field(app, "translation_service", None)
        if not settings.translation_enabled:
            return

        provider = settings.translation_provider.strip().lower()
        if provider != "azure":
            logger.warning(
                "backend_translation_startup_skipped_unknown_provider",
                extra={"translation_provider": provider},
            )
            set_runtime_field(app, "translation_error", f"Unknown translation provider '{provider}'.")
            return

        if settings.translation_azure_api_key and settings.translation_azure_region:
            try:
                set_service_field(
                    app,
                    "translation_service",
                    AzureTranslationService(
                        api_key=settings.translation_azure_api_key,
                        region=settings.translation_azure_region,
                        endpoint=settings.translation_azure_endpoint,
                        api_version=settings.translation_azure_api_version,
                    ),
                )
            except Exception:
                logger.exception("backend_translation_startup_failed")
                set_runtime_field(app, "translation_error", "Failed to initialize Azure translation service.")
        else:
            logger.warning("backend_translation_startup_skipped_missing_azure_config")
            set_runtime_field(
                app,
                "translation_error",
                "Missing DANOTE_TRANSLATION_AZURE_API_KEY or DANOTE_TRANSLATION_AZURE_REGION.",
            )

    log_timed_startup_step("translation", operation)


def _init_word_verification(app: FastAPI, settings: Settings) -> None:
    def operation() -> None:
        set_runtime_field(app, "word_verification_error", None)
        set_service_field(app, "word_verification_service", None)
        if not settings.word_verification_enabled:
            return
        if settings.word_verification_gemini_api_key:
            try:
                set_service_field(
                    app,
                    "word_verification_service",
                    GeminiWordVerificationService(
                        api_key=settings.word_verification_gemini_api_key,
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

    log_timed_startup_step("word_verification", operation)


def _init_tts(app: FastAPI, settings: Settings) -> None:
    def operation() -> None:
        set_runtime_field(app, "tts_error", None)
        set_service_field(app, "tts_service", None)
        if not settings.tts_enabled:
            return

        provider = settings.tts_provider.strip().lower()
        if provider != "azure":
            logger.warning(
                "backend_tts_startup_skipped_unknown_provider",
                extra={"tts_provider": provider},
            )
            set_runtime_field(app, "tts_error", f"Unknown TTS provider '{provider}'.")
            return

        if settings.tts_azure_api_key and settings.tts_azure_region:
            try:
                set_service_field(
                    app,
                    "tts_service",
                    AzureSpeechTTSService(
                        api_key=settings.tts_azure_api_key,
                        region=settings.tts_azure_region,
                        endpoint=settings.tts_azure_endpoint,
                        voice_name=settings.tts_azure_voice_name,
                    ),
                )
            except Exception:
                logger.exception("backend_tts_startup_failed")
                set_runtime_field(app, "tts_error", "Failed to initialize Azure Speech TTS service.")
        else:
            logger.warning("backend_tts_startup_skipped_missing_azure_config")
            set_runtime_field(
                app,
                "tts_error",
                "Missing DANOTE_TTS_AZURE_API_KEY or DANOTE_TTS_AZURE_REGION.",
            )

    log_timed_startup_step("tts", operation)
