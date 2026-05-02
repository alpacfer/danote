from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.app_state import set_service_field
from app.core.config import Settings
from app.db.migrations import apply_migrations
from app.main import create_app
from tests.api.wordbank_test_support import build_test_settings


def build_api_test_app(
    db_path: Path,
    *,
    nlp_adapter_factory: Callable[[Settings], Any],
    cor_local_db_path: Path | None = None,
    apply_db_migrations: bool = True,
    service_overrides: dict[str, Any] | None = None,
) -> FastAPI:
    if apply_db_migrations:
        apply_migrations(db_path)

    app = create_app(
        build_test_settings(db_path, cor_local_db_path=cor_local_db_path, nlp_enabled=True),
        nlp_adapter_factory=nlp_adapter_factory,
    )
    for field_name, value in (service_overrides or {}).items():
        set_service_field(app, field_name, value)
    return app


@contextmanager
def api_test_client(
    db_path: Path,
    *,
    nlp_adapter_factory: Callable[[Settings], Any],
    cor_local_db_path: Path | None = None,
    apply_db_migrations: bool = True,
    service_overrides: dict[str, Any] | None = None,
) -> Iterator[TestClient]:
    app = build_api_test_app(
        db_path,
        nlp_adapter_factory=nlp_adapter_factory,
        cor_local_db_path=cor_local_db_path,
        apply_db_migrations=apply_db_migrations,
        service_overrides=service_overrides,
    )
    with TestClient(app) as client:
        yield client
