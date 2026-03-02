from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import Settings, load_settings
from app.db.migrations import apply_migrations
from app.core.logging import configure_logging
from app.nlp.adapter import NLPAdapter
from app.services.translation import DeepLTranslationService, GeminiTranslationService
from app.services.typo.typo_engine import TypoEngine
from app.services.verification import GeminiWordVerificationService

configure_logging()
logger = logging.getLogger(__name__)


def _default_nlp_adapter_factory(settings: Settings) -> NLPAdapter:
    # Import lazily so missing NLP dependencies degrade health instead of crashing import.
    from app.nlp.danish import load_danish_nlp_adapter

    return load_danish_nlp_adapter(settings)


def create_app(
    settings: Settings | None = None,
    nlp_adapter_factory: Callable[[Settings], NLPAdapter] = _default_nlp_adapter_factory,
) -> FastAPI:
    app_settings = settings or load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        applied: list[str] = []

        try:
            app_settings.db_path.parent.mkdir(parents=True, exist_ok=True)
            applied = apply_migrations(app_settings.db_path)
            app.state.db_ready = True
            app.state.db_error = None
        except Exception as exc:
            app.state.db_ready = False
            app.state.db_error = str(exc)
            logger.exception(
                "backend_db_startup_failed",
                extra={"db_path": str(app_settings.db_path)},
            )

        adapter: NLPAdapter | None = None
        try:
            adapter = nlp_adapter_factory(app_settings)
            app.state.nlp_ready = True
            app.state.nlp_error = None
        except Exception as exc:
            app.state.nlp_ready = False
            app.state.nlp_error = str(exc)
            logger.exception(
                "backend_nlp_startup_failed",
                extra={"nlp_model": app_settings.nlp_model},
            )
        app.state.nlp_adapter = adapter
        typo_engine = None
        if app_settings.typo_enabled and app.state.db_ready:
            resources_path = Path(__file__).resolve().parents[1] / "resources" / "dictionaries"
            configured_dictionary_path = app_settings.typo_dictionary_path
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
                    db_path=app_settings.db_path,
                    dictionary_paths=dictionary_paths,
                )
            except Exception:
                logger.exception("backend_typo_engine_startup_failed")
                typo_engine = None
        app.state.typo_engine = typo_engine
        app.state.translation_error = None
        if app_settings.translation_enabled:
            provider = app_settings.translation_provider.strip().lower()
            if provider == "gemini":
                if app_settings.translation_gemini_api_key:
                    try:
                        app.state.translation_service = GeminiTranslationService(
                            api_key=app_settings.translation_gemini_api_key,
                            model=app_settings.translation_gemini_model,
                        )
                    except Exception:
                        logger.exception("backend_translation_startup_failed")
                        app.state.translation_error = "Failed to initialize Gemini translation service."
                        app.state.translation_service = None
                else:
                    logger.warning("backend_translation_startup_skipped_missing_gemini_key")
                    app.state.translation_error = "Missing DANOTE_GEMINI_API_KEY."
                    app.state.translation_service = None
            elif provider == "deepl":
                if app_settings.translation_deepl_api_key:
                    try:
                        app.state.translation_service = DeepLTranslationService(
                            api_key=app_settings.translation_deepl_api_key,
                            base_url=app_settings.translation_deepl_api_url,
                        )
                    except Exception:
                        logger.exception("backend_translation_startup_failed")
                        app.state.translation_error = "Failed to initialize DeepL translation service."
                        app.state.translation_service = None
                else:
                    logger.warning("backend_translation_startup_skipped_missing_deepl_key")
                    app.state.translation_error = "Missing DANOTE_DEEPL_API_KEY."
                    app.state.translation_service = None
            else:
                logger.warning(
                    "backend_translation_startup_skipped_unknown_provider",
                    extra={"translation_provider": provider},
                )
                app.state.translation_error = f"Unknown translation provider '{provider}'."
                app.state.translation_service = None
        else:
            app.state.translation_service = None
        app.state.word_verification_error = None
        if app_settings.word_verification_enabled:
            if app_settings.word_verification_gemini_api_key:
                try:
                    app.state.word_verification_service = GeminiWordVerificationService(
                        api_key=app_settings.word_verification_gemini_api_key,
                        model=app_settings.word_verification_gemini_model,
                    )
                except Exception:
                    logger.exception("backend_word_verification_startup_failed")
                    app.state.word_verification_error = "Failed to initialize Gemini word verification service."
                    app.state.word_verification_service = None
            else:
                logger.warning("backend_word_verification_startup_skipped_missing_gemini_key")
                app.state.word_verification_error = "Missing DANOTE_WORD_VERIFICATION_GEMINI_API_KEY."
                app.state.word_verification_service = None
        else:
            app.state.word_verification_service = None

        startup_status = "ok" if app.state.db_ready and app.state.nlp_ready else "degraded"
        logger.info(
            "backend_startup",
            extra={
                "status": startup_status,
                "environment": app_settings.environment,
                "db_path": str(app_settings.db_path),
                "host": app_settings.host,
                "port": app_settings.port,
                "applied_migrations": applied,
                "db_error": app.state.db_error,
                "nlp_error": app.state.nlp_error,
                "nlp": adapter.metadata() if adapter else None,
                "typo_enabled": bool(typo_engine is not None),
                "translation_enabled": app_settings.translation_enabled,
                "translation_error": app.state.translation_error,
                "translation_provider": (
                    getattr(app.state.translation_service, "provider", None)
                    if app.state.translation_service
                    else None
                ),
                "word_verification_enabled": app_settings.word_verification_enabled,
                "word_verification_error": app.state.word_verification_error,
                "word_verification_provider": (
                    getattr(app.state.word_verification_service, "provider", None)
                    if app.state.word_verification_service
                    else None
                ),
            },
        )
        yield
        translation_service = getattr(app.state, "translation_service", None)
        close = getattr(translation_service, "close", None)
        if callable(close):
            close()
        verification_service = getattr(app.state, "word_verification_service", None)
        verification_close = getattr(verification_service, "close", None)
        if callable(verification_close):
            verification_close()

    app = FastAPI(title="Danote Backend", version="0.1.0", lifespan=lifespan)
    app.state.settings = app_settings
    app.state.db_ready = False
    app.state.db_error = None
    app.state.nlp_ready = False
    app.state.nlp_error = None
    app.state.nlp_adapter = None
    app.state.typo_engine = None
    app.state.translation_service = None
    app.state.translation_error = None
    app.state.runtime_api_keys = {}
    app.state.word_verification_service = None
    app.state.word_verification_error = None
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(app_settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix="/api")
    return app


app = create_app()
