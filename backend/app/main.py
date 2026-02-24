from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import Settings, load_settings
from app.db.migrations import apply_migrations
from app.core.logging import configure_logging
from app.nlp.adapter import NLPAdapter

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
            },
        )
        yield

    app = FastAPI(title="Danote Backend", version="0.1.0", lifespan=lifespan)
    app.state.settings = app_settings
    app.state.db_ready = False
    app.state.db_error = None
    app.state.nlp_ready = False
    app.state.nlp_error = None
    app.state.nlp_adapter = None
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
