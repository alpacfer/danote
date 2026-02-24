from __future__ import annotations

from app.core.config import load_settings


def test_load_settings_parses_cors_origins_from_env(monkeypatch) -> None:
    monkeypatch.setenv(
        "DANOTE_CORS_ORIGINS",
        "http://127.0.0.1:4173, http://localhost:5173 ,",
    )

    settings = load_settings()

    assert settings.cors_origins == ("http://127.0.0.1:4173", "http://localhost:5173")

