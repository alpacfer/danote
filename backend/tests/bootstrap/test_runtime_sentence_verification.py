from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from app.bootstrap.runtime_sentence_verification import initialize_sentence_verification
from app.core.app_state import get_runtime_state, init_app_state
from app.core.config import Settings


def _settings(tmp_path: Path, **overrides) -> Settings:
    return Settings(
        environment="test",
        app_name="danote-backend-test",
        host="127.0.0.1",
        port=8001,
        db_path=tmp_path / "danote.sqlite3",
        nlp_model="stub-model",
        **overrides,
    )


class StubSentenceVerificationService:
    provider = "gemini_sentence_verification"

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def close(self) -> None:
        return None


def test_initialize_sentence_verification_key_present_sets_service(monkeypatch, tmp_path: Path) -> None:
    app = FastAPI()
    settings = _settings(
        tmp_path,
        gemini_api_key="test-gemini-key",
        gemini_model="gemini-3.1-flash-lite-preview",
    )
    init_app_state(app, settings)

    monkeypatch.setattr(
        "app.bootstrap.runtime_sentence_verification.GeminiSentenceVerificationService",
        StubSentenceVerificationService,
    )

    initialize_sentence_verification(app, settings)

    runtime = get_runtime_state(app)
    assert runtime.sentence_verification_error is None
    assert runtime.services.sentence_verification_service is not None
    assert runtime.services.sentence_verification_service.api_key == "test-gemini-key"
    assert runtime.services.sentence_verification_service.model == "gemini-3.1-flash-lite-preview"


def test_initialize_sentence_verification_uses_word_verification_fallbacks(
    monkeypatch,
    tmp_path: Path,
) -> None:
    app = FastAPI()
    settings = _settings(
        tmp_path,
        gemini_api_key=None,
        gemini_model="gemini-3.1-flash-lite-preview",
        word_verification_gemini_api_key="test-word-verification-key",
        word_verification_gemini_model="gemini-3-flash-preview",
    )
    init_app_state(app, settings)

    monkeypatch.setattr(
        "app.bootstrap.runtime_sentence_verification.GeminiSentenceVerificationService",
        StubSentenceVerificationService,
    )

    initialize_sentence_verification(app, settings)

    runtime = get_runtime_state(app)
    assert runtime.sentence_verification_error is None
    assert runtime.services.sentence_verification_service is not None
    assert runtime.services.sentence_verification_service.api_key == "test-word-verification-key"
    assert runtime.services.sentence_verification_service.model == "gemini-3-flash-preview"


def test_initialize_sentence_verification_key_absent_leaves_service_none(tmp_path: Path) -> None:
    app = FastAPI()
    settings = _settings(
        tmp_path,
        gemini_api_key=None,
    )
    init_app_state(app, settings)

    initialize_sentence_verification(app, settings)

    runtime = get_runtime_state(app)
    assert runtime.services.sentence_verification_service is None
    assert runtime.sentence_verification_error == "Missing DANOTE_GEMINI_API_KEY."
