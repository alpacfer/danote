from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI, Request

from app.core.config import Settings


@dataclass(slots=True)
class BackendServices:
    nlp_adapter: Any = None
    cor_lexicon_service: Any = None
    cor_local_lexicon_service: Any = None
    en_local_lexicon_service: Any = None
    en_gemini_translation_service: Any = None
    translation_service: Any = None
    gemini_word_translation_service: Any = None
    gemini_related_words_service: Any = None
    word_verification_service: Any = None
    sentence_verification_service: Any = None
    tts_service: Any = None


@dataclass(slots=True)
class BackendRuntimeState:
    settings: Settings
    services: BackendServices = field(default_factory=BackendServices)
    runtime_api_keys: dict[str, str | None] = field(default_factory=dict)
    background_worker: Any = None
    key_encryption: Any = None
    users_repository: Any = None
    user_api_keys_repository: Any = None
    clerk_jwks_client: Any = None
    user_service_resolver: Any = None
    auth_error: str | None = None
    db_ready: bool = False
    db_error: str | None = None
    nlp_ready: bool = False
    nlp_error: str | None = None
    cor_lookup_error: str | None = None
    cor_local_lookup_error: str | None = None
    en_local_lookup_error: str | None = None
    en_gemini_translation_error: str | None = None
    translation_error: str | None = None
    gemini_word_translation_error: str | None = None
    related_words_error: str | None = None
    word_verification_error: str | None = None
    sentence_verification_error: str | None = None
    tts_error: str | None = None


def init_app_state(app: FastAPI, settings: Settings) -> BackendRuntimeState:
    runtime = BackendRuntimeState(settings=settings)
    app.state.runtime = runtime
    return runtime


def get_runtime_state(target: FastAPI | Request) -> BackendRuntimeState:
    app = target.app if isinstance(target, Request) else target
    return app.state.runtime


def get_settings(target: FastAPI | Request) -> Settings:
    return get_runtime_state(target).settings


def get_services(target: FastAPI | Request) -> BackendServices:
    return get_runtime_state(target).services


def get_user_service_resolver(target: FastAPI | Request) -> Any:
    return get_runtime_state(target).user_service_resolver


def resolve_services_for_user(target: FastAPI | Request, user_id: int) -> BackendServices:
    """Return a per-user `BackendServices` bundle, falling back to host singletons."""
    resolver = get_user_service_resolver(target)
    if resolver is None:
        return get_services(target)
    return resolver.resolve(user_id)


def set_runtime_field(app: FastAPI, field_name: str, value: Any) -> None:
    runtime = get_runtime_state(app)
    setattr(runtime, field_name, value)


def set_service_field(app: FastAPI, field_name: str, value: Any) -> None:
    runtime = get_runtime_state(app)
    setattr(runtime.services, field_name, value)


def close_runtime_services(app: FastAPI) -> None:
    runtime = get_runtime_state(app)
    worker = runtime.background_worker
    stop = getattr(worker, "stop", None)
    if callable(stop):
        stop()

    services = get_services(app)
    for field_name in (
        "cor_lexicon_service",
        "translation_service",
        "gemini_word_translation_service",
        "gemini_related_words_service",
        "en_gemini_translation_service",
        "word_verification_service",
        "sentence_verification_service",
        "tts_service",
    ):
        service = getattr(services, field_name, None)
        close = getattr(service, "close", None)
        if callable(close):
            close()
