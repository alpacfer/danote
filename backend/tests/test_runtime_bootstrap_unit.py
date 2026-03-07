from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from app.bootstrap.runtime import build_startup_steps
from app.bootstrap.runtime_translation import initialize_translation
from app.bootstrap.runtime_tts import initialize_tts
from app.bootstrap.runtime_word_verification import initialize_word_verification
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


def test_build_startup_steps_registers_expected_sequence(stub_nlp_adapter_factory) -> None:
    steps = build_startup_steps(stub_nlp_adapter_factory)

    assert [step.name for step in steps] == [
        "nlp",
        "cor_local",
        "cor",
        "typo",
        "translation",
        "word_verification",
        "tts",
    ]


def test_initialize_translation_uses_runtime_overrides(monkeypatch, tmp_path: Path) -> None:
    app = FastAPI()
    settings = _settings(
        tmp_path,
        translation_enabled=True,
        translation_azure_api_key=None,
        translation_azure_region=None,
    )
    init_app_state(app, settings)

    class StubTranslationService:
        provider = "azure_translator"

        def __init__(self, api_key: str, region: str, endpoint: str | None, api_version: str):
            self.api_key = api_key
            self.region = region
            self.endpoint = endpoint
            self.api_version = api_version

        def close(self) -> None:
            return None

    monkeypatch.setattr("app.bootstrap.runtime_translation.AzureTranslationService", StubTranslationService)

    initialize_translation(
        app,
        settings,
        {
            "translation_azure_api_key": "runtime-key",
            "translation_azure_region": "westeurope",
        },
    )

    runtime = get_runtime_state(app)
    assert runtime.translation_error is None
    assert runtime.services.translation_service is not None
    assert runtime.services.translation_service.api_key == "runtime-key"
    assert runtime.services.translation_service.region == "westeurope"


def test_initialize_tts_disabled_leaves_service_unset(tmp_path: Path) -> None:
    app = FastAPI()
    settings = _settings(tmp_path, tts_enabled=False)
    init_app_state(app, settings)

    initialize_tts(app, settings)

    runtime = get_runtime_state(app)
    assert runtime.tts_error is None
    assert runtime.services.tts_service is None


def test_initialize_word_verification_missing_key_sets_runtime_error(tmp_path: Path) -> None:
    app = FastAPI()
    settings = _settings(
        tmp_path,
        word_verification_enabled=True,
        word_verification_gemini_api_key=None,
    )
    init_app_state(app, settings)

    initialize_word_verification(app, settings)

    runtime = get_runtime_state(app)
    assert runtime.services.word_verification_service is None
    assert runtime.word_verification_error == "Missing DANOTE_WORD_VERIFICATION_GEMINI_API_KEY."
