from __future__ import annotations

from pathlib import Path

from app.core.config import load_settings


def test_load_settings_parses_cors_origins_from_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv(
        "DANOTE_CORS_ORIGINS",
        "http://127.0.0.1:4173, http://localhost:5173 ,",
    )

    settings = load_settings(env_file=tmp_path / "missing.env")

    assert settings.cors_origins == ("http://127.0.0.1:4173", "http://localhost:5173")


def test_load_settings_defaults_include_vite_dev_origins(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DANOTE_CORS_ORIGINS", raising=False)

    settings = load_settings(env_file=tmp_path / "missing.env")

    assert "http://127.0.0.1:5173" in settings.cors_origins
    assert "http://localhost:5173" in settings.cors_origins
    assert "http://127.0.0.1:4173" in settings.cors_origins
    assert "http://localhost:4173" in settings.cors_origins


def test_load_settings_defaults_to_deepl_provider(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DANOTE_TRANSLATION_PROVIDER", raising=False)
    monkeypatch.delenv("DANOTE_TRANSLATION_DEEPL_API_KEY", raising=False)
    monkeypatch.delenv("DANOTE_TRANSLATION_DEEPL_ENDPOINT", raising=False)
    monkeypatch.delenv("DANOTE_TRANSLATION_AZURE_API_VERSION", raising=False)
    monkeypatch.delenv("DANOTE_TTS_PROVIDER", raising=False)
    monkeypatch.delenv("DANOTE_TTS_AZURE_VOICE_NAME", raising=False)
    monkeypatch.delenv("DANOTE_WORD_VERIFICATION_ENABLED", raising=False)
    monkeypatch.delenv("DANOTE_GEMINI_MODEL", raising=False)
    monkeypatch.delenv("DANOTE_SEARCH_WARMUP", raising=False)

    settings = load_settings(env_file=tmp_path / "missing.env")

    assert settings.translation_provider == "deepl"
    assert settings.translation_azure_api_version == "3.0"
    assert settings.translation_deepl_api_key is None
    assert settings.translation_deepl_endpoint is None
    assert settings.gemini_model == "gemini-3.1-flash-lite"
    assert settings.tts_provider == "azure"
    assert settings.tts_azure_voice_name == "da-DK-ChristelNeural"
    assert settings.word_verification_enabled is True
    assert settings.search_warmup_enabled is True


def test_load_settings_can_disable_search_warmup(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DANOTE_SEARCH_WARMUP", "0")

    settings = load_settings(env_file=tmp_path / "missing.env")

    assert settings.search_warmup_enabled is False


def test_load_settings_does_not_ship_default_api_keys(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DANOTE_TRANSLATION_DEEPL_API_KEY", raising=False)
    monkeypatch.delenv("DANOTE_TRANSLATION_DEEPL_ENDPOINT", raising=False)
    monkeypatch.delenv("DANOTE_TRANSLATION_AZURE_API_KEY", raising=False)
    monkeypatch.delenv("DANOTE_TRANSLATION_AZURE_REGION", raising=False)
    monkeypatch.delenv("DANOTE_TTS_AZURE_API_KEY", raising=False)
    monkeypatch.delenv("DANOTE_TTS_AZURE_REGION", raising=False)
    monkeypatch.delenv("DANOTE_GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("DANOTE_WORD_VERIFICATION_GEMINI_API_KEY", raising=False)

    settings = load_settings(env_file=tmp_path / "missing.env")

    assert settings.translation_deepl_api_key is None
    assert settings.translation_deepl_endpoint is None
    assert settings.translation_azure_api_key is None
    assert settings.translation_azure_region is None
    assert settings.tts_azure_api_key is None
    assert settings.tts_azure_region is None
    assert settings.gemini_api_key is None
    assert settings.word_verification_gemini_api_key is None


def test_load_settings_uses_shared_gemini_defaults_for_compatibility(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DANOTE_GEMINI_API_KEY", "shared-key")
    monkeypatch.setenv("DANOTE_GEMINI_MODEL", "gemini-custom")
    monkeypatch.delenv("DANOTE_WORD_VERIFICATION_GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("DANOTE_WORD_VERIFICATION_GEMINI_MODEL", raising=False)

    settings = load_settings(env_file=tmp_path / "missing.env")

    assert settings.gemini_api_key == "shared-key"
    assert settings.gemini_model == "gemini-custom"
    assert settings.word_verification_gemini_api_key == "shared-key"
    assert settings.word_verification_gemini_model == "gemini-custom"


def test_load_settings_reads_api_keys_from_env_local(monkeypatch, tmp_path: Path) -> None:
    env_file = tmp_path / ".env.local"
    env_file.write_text(
        "\n".join(
            [
                "DANOTE_TRANSLATION_AZURE_API_KEY=translator-key",
                "DANOTE_TRANSLATION_AZURE_REGION=westeurope",
                "DANOTE_TRANSLATION_DEEPL_API_KEY=deepl-key",
                "DANOTE_TRANSLATION_DEEPL_ENDPOINT=https://api-free.deepl.com",
                "DANOTE_TTS_AZURE_API_KEY=speech-key",
                "DANOTE_TTS_AZURE_REGION=westeurope",
                "DANOTE_GEMINI_API_KEY=gemini-key",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("DANOTE_TRANSLATION_DEEPL_API_KEY", raising=False)
    monkeypatch.delenv("DANOTE_TRANSLATION_DEEPL_ENDPOINT", raising=False)
    monkeypatch.delenv("DANOTE_TRANSLATION_AZURE_API_KEY", raising=False)
    monkeypatch.delenv("DANOTE_TRANSLATION_AZURE_REGION", raising=False)
    monkeypatch.delenv("DANOTE_TTS_AZURE_API_KEY", raising=False)
    monkeypatch.delenv("DANOTE_TTS_AZURE_REGION", raising=False)
    monkeypatch.delenv("DANOTE_GEMINI_API_KEY", raising=False)

    settings = load_settings(env_file=env_file)

    assert settings.translation_deepl_api_key == "deepl-key"
    assert settings.translation_deepl_endpoint == "https://api-free.deepl.com"
    assert settings.translation_azure_api_key == "translator-key"
    assert settings.translation_azure_region == "westeurope"
    assert settings.tts_azure_api_key == "speech-key"
    assert settings.tts_azure_region == "westeurope"
    assert settings.gemini_api_key == "gemini-key"


def test_load_settings_resolves_relative_paths_from_repo_root(monkeypatch, tmp_path: Path) -> None:
    env_file = tmp_path / ".env.local"
    env_file.write_text(
        "\n".join(
            [
                "DANOTE_DB_PATH=backend/data/custom.sqlite3",
                "DANOTE_COR_LOCAL_DB_PATH=backend/resources/dictionaries/cor.sqlite",
                "DANOTE_EN_LOCAL_DB_PATH=backend/resources/dictionaries/english_wiki.sqlite",
                "DANOTE_GEMINI_CHANGES_LOG_PATH=backend/data/gemini-applied-changes.jsonl",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("DANOTE_DB_PATH", raising=False)
    monkeypatch.delenv("DANOTE_COR_LOCAL_DB_PATH", raising=False)
    monkeypatch.delenv("DANOTE_EN_LOCAL_DB_PATH", raising=False)
    monkeypatch.delenv("DANOTE_GEMINI_CHANGES_LOG_PATH", raising=False)
    monkeypatch.chdir(Path(__file__).resolve().parents[2])

    settings = load_settings(env_file=env_file)

    repo_dir = Path(__file__).resolve().parents[3]
    assert settings.db_path == repo_dir / "backend/data/custom.sqlite3"
    assert settings.cor_local_db_path == repo_dir / "backend/resources/dictionaries/cor.sqlite"
    assert settings.en_local_db_path == repo_dir / "backend/resources/dictionaries/english_wiki.sqlite"
    assert settings.gemini_changes_log_path == repo_dir / "backend/data/gemini-applied-changes.jsonl"
