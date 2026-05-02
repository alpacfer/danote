from __future__ import annotations

from pathlib import Path

from app.core.app_state import BackendRuntimeState
from app.core.config import Settings
from app.services.use_cases.health_status import build_health_status


def _settings(**overrides: object) -> Settings:
    base = dict(
        environment="test",
        app_name="danote-backend-test",
        host="127.0.0.1",
        port=8001,
        db_path=Path("/tmp/danote-health.sqlite3"),
        nlp_model="retired-dacy-disabled",
        translation_enabled=True,
        translation_provider="deepl",
        tts_enabled=True,
        tts_provider="azure",
    )
    base.update(overrides)
    return Settings(**base)


def test_build_health_status_marks_disabled_components() -> None:
    runtime = BackendRuntimeState(
        settings=_settings(translation_enabled=False, tts_enabled=False, nlp_enabled=False),
        db_ready=True,
        nlp_ready=False,
    )

    payload = build_health_status(runtime)

    assert payload.status == "ok"
    assert payload.components["translation"] == "disabled"
    assert payload.components["tts"] == "disabled"
    assert payload.apis["deepl_translator"].status == "disabled"
    assert payload.apis["azure_speech"].status == "disabled"


def test_build_health_status_marks_missing_keys_for_selected_providers() -> None:
    runtime = BackendRuntimeState(settings=_settings(), db_ready=True, nlp_ready=True)

    payload = build_health_status(runtime)

    assert payload.apis["deepl_translator"].status == "missing_key"
    assert payload.apis["deepl_translator"].configured is False
    assert payload.apis["azure_translator"].status == "inactive"
    assert payload.apis["azure_speech"].status == "missing_key"


def test_build_health_status_marks_degraded_with_key_and_error() -> None:
    runtime = BackendRuntimeState(
        settings=_settings(translation_deepl_api_key="key", tts_azure_api_key="key", tts_azure_region="westeurope"),
        db_ready=True,
        nlp_ready=True,
        translation_error="translation boot failed",
        tts_error="tts boot failed",
    )

    payload = build_health_status(runtime)

    assert payload.components["translation"] == "degraded"
    assert payload.components["tts"] == "degraded"
    assert payload.apis["deepl_translator"].status == "degraded"
    assert payload.apis["deepl_translator"].message == "translation boot failed"
    assert payload.apis["azure_speech"].status == "degraded"
    assert payload.apis["azure_speech"].message == "tts boot failed"


def test_build_health_status_handles_gemini_missing_and_degraded() -> None:
    missing_key_runtime = BackendRuntimeState(settings=_settings(), db_ready=True, nlp_ready=True)
    missing_key_payload = build_health_status(missing_key_runtime)
    assert missing_key_payload.apis["gemini"].status == "missing_key"

    degraded_runtime = BackendRuntimeState(
        settings=_settings(gemini_api_key="gemini-key"),
        db_ready=True,
        nlp_ready=True,
        gemini_word_translation_error="gemini init failed",
    )
    degraded_payload = build_health_status(degraded_runtime)
    assert degraded_payload.apis["gemini"].status == "degraded"
    assert degraded_payload.apis["gemini"].message == "gemini init failed"
