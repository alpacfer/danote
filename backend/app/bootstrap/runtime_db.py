from __future__ import annotations

import logging

from fastapi import FastAPI

from app.core.app_state import set_runtime_field
from app.core.config import Settings
from app.db.migrations import apply_migrations

logger = logging.getLogger(__name__)


def initialize_database(app: FastAPI, settings: Settings) -> list[str]:
    try:
        settings.db_path.parent.mkdir(parents=True, exist_ok=True)
        applied = apply_migrations(settings.db_path)
        set_runtime_field(app, "db_ready", True)
        set_runtime_field(app, "db_error", None)
        return applied
    except Exception as exc:
        set_runtime_field(app, "db_ready", False)
        set_runtime_field(app, "db_error", str(exc))
        logger.exception("backend_db_startup_failed", extra={"db_path": str(settings.db_path)})
        return []
