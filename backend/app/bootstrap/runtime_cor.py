from __future__ import annotations

import logging

from fastapi import FastAPI

from app.core.app_state import set_runtime_field, set_service_field
from app.core.config import Settings
from app.services.cor import CORLexiconService
from app.services.cor_local import CORLocalLexiconService

logger = logging.getLogger(__name__)


def initialize_cor_local(app: FastAPI, settings: Settings) -> None:
    set_service_field(
        app,
        "cor_local_lexicon_service",
        CORLocalLexiconService(db_path=settings.cor_local_db_path),
    )
    set_runtime_field(app, "cor_local_lookup_error", None)


def initialize_cor(app: FastAPI, settings: Settings) -> None:
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
