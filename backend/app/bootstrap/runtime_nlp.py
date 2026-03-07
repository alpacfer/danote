from __future__ import annotations

import logging
from collections.abc import Callable

from fastapi import FastAPI

from app.core.app_state import set_runtime_field, set_service_field
from app.core.config import Settings
from app.nlp.adapter import NLPAdapter

logger = logging.getLogger(__name__)


def initialize_nlp(
    app: FastAPI,
    settings: Settings,
    factory: Callable[[Settings], NLPAdapter],
) -> None:
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
