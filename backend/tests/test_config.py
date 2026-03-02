from __future__ import annotations

from app.core.config import load_settings


def test_load_settings_parses_cors_origins_from_env(monkeypatch) -> None:
    monkeypatch.setenv(
        "DANOTE_CORS_ORIGINS",
        "http://127.0.0.1:4173, http://localhost:5173 ,",
    )

    settings = load_settings()

    assert settings.cors_origins == ("http://127.0.0.1:4173", "http://localhost:5173")


def test_load_settings_defaults_to_deepl_with_gemini_flash_model_available(monkeypatch) -> None:
    monkeypatch.delenv("DANOTE_TRANSLATION_PROVIDER", raising=False)
    monkeypatch.delenv("DANOTE_GEMINI_MODEL", raising=False)
    monkeypatch.delenv("DANOTE_WORD_VERIFICATION_ENABLED", raising=False)

    settings = load_settings()

    assert settings.translation_provider == "deepl"
    assert settings.translation_gemini_model == "gemini-3-flash-preview"
    assert settings.word_verification_enabled is True


def test_load_settings_does_not_ship_default_api_keys(monkeypatch) -> None:
    monkeypatch.delenv("DANOTE_GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("DANOTE_DEEPL_API_KEY", raising=False)
    monkeypatch.delenv("DANOTE_WORD_VERIFICATION_GEMINI_API_KEY", raising=False)

    settings = load_settings()

    assert settings.translation_gemini_api_key is None
    assert settings.translation_deepl_api_key is None
    assert settings.word_verification_gemini_api_key is None
