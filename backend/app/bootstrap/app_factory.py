from __future__ import annotations

import time
from collections.abc import Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.bootstrap.runtime import default_nlp_adapter_factory, startup_lifespan
from app.core.app_state import init_app_state
from app.core.config import Settings, load_settings
from app.core.logging import configure_logging
from app.nlp.adapter import NLPAdapter

configure_logging()


def create_app(
    settings: Settings | None = None,
    nlp_adapter_factory: Callable[[Settings], NLPAdapter] = default_nlp_adapter_factory,
) -> FastAPI:
    app_settings = settings or load_settings()
    app = FastAPI(
        title="Danote Backend",
        version="0.1.0",
        lifespan=startup_lifespan(app_settings, nlp_adapter_factory),
    )
    init_app_state(app, app_settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(app_settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    _install_request_timing_middleware(app)
    app.include_router(api_router, prefix="/api")
    return app


def _install_request_timing_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_timing_middleware(request: Request, call_next):
        started_at = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        response.headers["X-Process-Time-Ms"] = str(duration_ms)
        return response
