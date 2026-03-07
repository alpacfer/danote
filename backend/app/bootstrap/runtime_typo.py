from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI

from app.core.app_state import get_runtime_state, set_service_field
from app.core.config import Settings
from app.services.typo.typo_engine import TypoEngine

logger = logging.getLogger(__name__)


def initialize_typo(app: FastAPI, settings: Settings) -> None:
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
