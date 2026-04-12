from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from app.bootstrap.runtime import build_startup_steps
from app.bootstrap.runtime_gemini_word_translation import initialize_gemini_word_translation
from app.bootstrap.runtime_translation import initialize_translation
from app.bootstrap.runtime_tts import initialize_tts
from app.bootstrap.runtime_word_verification import initialize_word_verification
from app.core.app_state import get_runtime_state, init_app_state
from app.core.config import Settings
from app.services.gemini_translation import GeminiTranslationError
from app.services.translation import TranslationError


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
        "translation",
        "gemini_word_translation",
        "related_words",
        "word_verification",
        "sentence_verification",
        "tts",
    ]


def test_initialize_translation_uses_runtime_overrides(monkeypatch, tmp_path: Path) -> None:
    app = FastAPI()
    settings = _settings(
        tmp_path,
        translation_provider="azure",
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


def test_initialize_translation_deepl_uses_runtime_overrides(monkeypatch, tmp_path: Path) -> None:
    app = FastAPI()
    settings = _settings(
        tmp_path,
        translation_provider="deepl",
        translation_enabled=True,
        translation_deepl_api_key=None,
    )
    init_app_state(app, settings)

    class StubDeepLTranslationService:
        provider = "deepl_translator"

        def __init__(self, api_key: str, endpoint: str | None):
            self.api_key = api_key
            self.endpoint = endpoint

        def close(self) -> None:
            return None

    monkeypatch.setattr("app.bootstrap.runtime_translation.DeepLTranslationService", StubDeepLTranslationService)

    initialize_translation(
        app,
        settings,
        {
            "translation_provider": "deepl",
            "translation_deepl_api_key": "runtime-deepl-key",
        },
    )

    runtime = get_runtime_state(app)
    assert runtime.translation_error is None
    assert runtime.services.translation_service is not None
    assert runtime.services.translation_service.api_key == "runtime-deepl-key"


def test_initialize_tts_disabled_leaves_service_unset(tmp_path: Path) -> None:
    app = FastAPI()
    settings = _settings(tmp_path, tts_enabled=False)
    init_app_state(app, settings)

    initialize_tts(app, settings)

    runtime = get_runtime_state(app)
    assert runtime.tts_error is None
    assert runtime.services.tts_service is None


def test_initialize_gemini_word_translation_uses_shared_gemini_settings(monkeypatch, tmp_path: Path) -> None:
    app = FastAPI()
    settings = _settings(tmp_path, gemini_api_key="shared-key", gemini_model="gemini-3.1-flash-lite-preview")
    init_app_state(app, settings)

    class StubGeminiWordTranslationService:
        provider = "gemini_word_translation"

        def __init__(self, api_key: str, model: str):
            self.api_key = api_key
            self.model = model

        def close(self) -> None:
            return None

    monkeypatch.setattr(
        "app.bootstrap.runtime_gemini_word_translation.GeminiFlashLiteWordTranslationService",
        StubGeminiWordTranslationService,
    )

    initialize_gemini_word_translation(app, settings)

    runtime = get_runtime_state(app)
    assert runtime.gemini_word_translation_error is None
    assert runtime.services.gemini_word_translation_service is not None
    assert runtime.services.gemini_word_translation_service.api_key == "shared-key"
    assert runtime.services.gemini_word_translation_service.model == "gemini-3.1-flash-lite-preview"


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


def test_initialize_word_verification_falls_back_to_shared_gemini_key(monkeypatch, tmp_path: Path) -> None:
    app = FastAPI()
    settings = _settings(
        tmp_path,
        gemini_api_key="shared-key",
        gemini_model="gemini-3.1-flash-lite-preview",
        word_verification_enabled=True,
        word_verification_gemini_api_key=None,
        word_verification_gemini_model="gemini-3.1-flash-lite-preview",
    )
    init_app_state(app, settings)

    class StubVerificationService:
        provider = "gemini"

        def __init__(self, api_key: str, model: str):
            self.api_key = api_key
            self.model = model

        def close(self) -> None:
            return None

    monkeypatch.setattr("app.bootstrap.runtime_word_verification.GeminiWordVerificationService", StubVerificationService)

    initialize_word_verification(app, settings)

    runtime = get_runtime_state(app)
    assert runtime.word_verification_error is None
    assert runtime.services.word_verification_service is not None
    assert runtime.services.word_verification_service.api_key == "shared-key"
    assert runtime.services.word_verification_service.model == "gemini-3.1-flash-lite-preview"


def test_initialize_translation_logs_structured_failure_payload(monkeypatch, caplog, tmp_path: Path) -> None:
    app = FastAPI()
    settings = _settings(
        tmp_path,
        translation_provider="azure",
        translation_enabled=True,
        translation_azure_api_key="key",
        translation_azure_region="region",
    )
    init_app_state(app, settings)

    class FailingTranslationService:
        def __init__(self, api_key: str, region: str, endpoint: str | None, api_version: str) -> None:
            raise TranslationError("bad startup")

    monkeypatch.setattr("app.bootstrap.runtime_translation.AzureTranslationService", FailingTranslationService)

    with caplog.at_level("WARNING"):
        initialize_translation(app, settings)

    runtime = get_runtime_state(app)
    assert runtime.translation_error == "Failed to initialize Azure translation service."
    record = next(r for r in caplog.records if r.message == "backend_translation_startup_failed")
    assert record.provider == "azure_translator"
    assert record.operation == "startup.initialize"
    assert record.failure_class == "TranslationError"
    assert record.retryable is False


def test_initialize_gemini_word_translation_logs_structured_failure_payload(monkeypatch, caplog, tmp_path: Path) -> None:
    app = FastAPI()
    settings = _settings(tmp_path, gemini_api_key="shared-key", gemini_model="gemini-3.1-flash-lite-preview")
    init_app_state(app, settings)

    class FailingGeminiService:
        def __init__(self, api_key: str, model: str) -> None:
            raise GeminiTranslationError("invalid model")

    monkeypatch.setattr(
        "app.bootstrap.runtime_gemini_word_translation.GeminiFlashLiteWordTranslationService",
        FailingGeminiService,
    )

    with caplog.at_level("WARNING"):
        initialize_gemini_word_translation(app, settings)

    runtime = get_runtime_state(app)
    assert runtime.gemini_word_translation_error == "Failed to initialize Gemini word translation service."
    record = next(r for r in caplog.records if r.message == "backend_gemini_word_translation_startup_failed")
    assert record.provider == "gemini_word_translation"
    assert record.operation == "startup.initialize"
    assert record.failure_class == "GeminiTranslationError"
    assert record.retryable is False
