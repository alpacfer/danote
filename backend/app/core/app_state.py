from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI, Request

from app.core.config import Settings


@dataclass(slots=True)
class BackendServices:
    nlp_adapter: Any = None
    typo_engine: Any = None
    cor_lexicon_service: Any = None
    cor_local_lexicon_service: Any = None
    translation_service: Any = None
    word_verification_service: Any = None
    tts_service: Any = None


@dataclass(slots=True)
class BackendRuntimeState:
    settings: Settings
    services: BackendServices = field(default_factory=BackendServices)
    runtime_api_keys: dict[str, str | None] = field(default_factory=dict)
    db_ready: bool = False
    db_error: str | None = None
    nlp_ready: bool = False
    nlp_error: str | None = None
    cor_lookup_error: str | None = None
    cor_local_lookup_error: str | None = None
    translation_error: str | None = None
    word_verification_error: str | None = None
    tts_error: str | None = None


_TOP_LEVEL_FIELDS = (
    "db_ready",
    "db_error",
    "nlp_ready",
    "nlp_error",
    "cor_lookup_error",
    "cor_local_lookup_error",
    "translation_error",
    "word_verification_error",
    "tts_error",
    "runtime_api_keys",
)
_SERVICE_FIELDS = (
    "nlp_adapter",
    "typo_engine",
    "cor_lexicon_service",
    "cor_local_lexicon_service",
    "translation_service",
    "word_verification_service",
    "tts_service",
)


def init_app_state(app: FastAPI, settings: Settings) -> BackendRuntimeState:
    runtime = BackendRuntimeState(settings=settings)
    app.state.runtime = runtime
    app.state.settings = settings
    _sync_runtime_to_legacy(app, runtime)
    return runtime


def get_runtime_state(target: FastAPI | Request) -> BackendRuntimeState:
    app = target.app if isinstance(target, Request) else target
    runtime = app.state.runtime
    _sync_legacy_to_runtime(app, runtime)
    return runtime


def get_settings(target: FastAPI | Request) -> Settings:
    return get_runtime_state(target).settings


def get_services(target: FastAPI | Request) -> BackendServices:
    return get_runtime_state(target).services


def set_runtime_field(app: FastAPI, field_name: str, value: Any) -> None:
    runtime = get_runtime_state(app)
    setattr(runtime, field_name, value)
    setattr(app.state, field_name, value)


def set_service_field(app: FastAPI, field_name: str, value: Any) -> None:
    runtime = get_runtime_state(app)
    setattr(runtime.services, field_name, value)
    setattr(app.state, field_name, value)


def close_runtime_services(app: FastAPI) -> None:
    services = get_services(app)
    for field_name in (
        "cor_lexicon_service",
        "translation_service",
        "word_verification_service",
        "tts_service",
    ):
        service = getattr(services, field_name, None)
        close = getattr(service, "close", None)
        if callable(close):
            close()


def _sync_runtime_to_legacy(app: FastAPI, runtime: BackendRuntimeState) -> None:
    for field_name in _TOP_LEVEL_FIELDS:
        setattr(app.state, field_name, getattr(runtime, field_name))
    for field_name in _SERVICE_FIELDS:
        setattr(app.state, field_name, getattr(runtime.services, field_name))


def _sync_legacy_to_runtime(app: FastAPI, runtime: BackendRuntimeState) -> None:
    if getattr(app.state, "settings", None) is not runtime.settings:
        app.state.settings = runtime.settings
    for field_name in _TOP_LEVEL_FIELDS:
        if hasattr(app.state, field_name):
            setattr(runtime, field_name, getattr(app.state, field_name))
    for field_name in _SERVICE_FIELDS:
        if hasattr(app.state, field_name):
            setattr(runtime.services, field_name, getattr(app.state, field_name))
