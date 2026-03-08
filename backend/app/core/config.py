from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
REPO_DIR = BASE_DIR.parent
DATA_DIR = BASE_DIR / "data"
DEFAULT_CORS_ORIGINS = ("http://127.0.0.1:4173", "http://localhost:4173")


@dataclass(frozen=True)
class Settings:
    environment: str
    app_name: str
    host: str
    port: int
    db_path: Path
    nlp_model: str
    nlp_enabled: bool = True
    cors_origins: tuple[str, ...] = DEFAULT_CORS_ORIGINS
    typo_enabled: bool = True
    typo_dictionary_path: Path | None = None
    translation_enabled: bool = True
    translation_provider: str = "azure"
    translation_azure_api_key: str | None = None
    translation_azure_region: str | None = None
    translation_azure_endpoint: str | None = None
    translation_azure_api_version: str = "3.0"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.1-flash-lite-preview"
    cor_lookup_enabled: bool = False
    cor_lookup_timeout_seconds: float = 4.0
    cor_local_db_path: Path = BASE_DIR / "resources" / "dictionaries" / "cor.sqlite"
    word_verification_enabled: bool = False
    word_verification_gemini_api_key: str | None = None
    word_verification_gemini_model: str = "gemini-3-flash-preview"
    tts_enabled: bool = True
    tts_provider: str = "azure"
    tts_azure_api_key: str | None = None
    tts_azure_region: str | None = None
    tts_azure_endpoint: str | None = None
    tts_azure_voice_name: str = "da-DK-ChristelNeural"
    gemini_changes_log_path: Path = DATA_DIR / "gemini-applied-changes.jsonl"


def load_settings(*, env_file: Path | None = None) -> Settings:
    env_values = _load_env_file(env_file or (REPO_DIR / ".env.local"))
    db_path = Path(_required_env("DANOTE_DB_PATH", env_values, DATA_DIR / "danote.sqlite3"))
    typo_dictionary_path = _optional_env("DANOTE_TYPO_DICTIONARY_PATH", env_values)
    raw_cors_origins = _required_env("DANOTE_CORS_ORIGINS", env_values, "")
    parsed_cors_origins = tuple(
        origin.strip()
        for origin in raw_cors_origins.split(",")
        if origin.strip()
    )
    return Settings(
        environment=_required_env("DANOTE_ENV", env_values, "development"),
        app_name=_required_env("DANOTE_APP_NAME", env_values, "danote-backend"),
        host=_required_env("DANOTE_HOST", env_values, "127.0.0.1"),
        port=int(_required_env("DANOTE_PORT", env_values, "8000")),
        db_path=db_path,
        nlp_model=_required_env("DANOTE_NLP_MODEL", env_values, "da_dacy_small_trf-0.2.0"),
        nlp_enabled=_required_env("DANOTE_NLP_ENABLED", env_values, "1").lower() not in {"0", "false", "no"},
        cors_origins=parsed_cors_origins or DEFAULT_CORS_ORIGINS,
        typo_enabled=_required_env("DANOTE_TYPO_ENABLED", env_values, "1").lower() not in {"0", "false", "no"},
        typo_dictionary_path=Path(typo_dictionary_path) if typo_dictionary_path else None,
        translation_enabled=_required_env("DANOTE_TRANSLATION_ENABLED", env_values, "1").lower()
        not in {"0", "false", "no"},
        translation_provider=_required_env("DANOTE_TRANSLATION_PROVIDER", env_values, "azure"),
        translation_azure_api_key=_optional_env("DANOTE_TRANSLATION_AZURE_API_KEY", env_values),
        translation_azure_region=_optional_env("DANOTE_TRANSLATION_AZURE_REGION", env_values),
        translation_azure_endpoint=_optional_env("DANOTE_TRANSLATION_AZURE_ENDPOINT", env_values),
        translation_azure_api_version=_required_env("DANOTE_TRANSLATION_AZURE_API_VERSION", env_values, "3.0"),
        gemini_api_key=_required_or_optional_env(
            "DANOTE_GEMINI_API_KEY",
            env_values,
            _optional_env("DANOTE_WORD_VERIFICATION_GEMINI_API_KEY", env_values),
        ),
        gemini_model=_required_env(
            "DANOTE_GEMINI_MODEL",
            env_values,
            _required_env("DANOTE_WORD_VERIFICATION_GEMINI_MODEL", env_values, "gemini-3.1-flash-lite-preview"),
        ),
        cor_lookup_enabled=_required_env("DANOTE_COR_LOOKUP_ENABLED", env_values, "1").lower() not in {"0", "false", "no"},
        cor_lookup_timeout_seconds=float(_required_env("DANOTE_COR_LOOKUP_TIMEOUT_SECONDS", env_values, "4.0")),
        cor_local_db_path=Path(
            _required_env("DANOTE_COR_LOCAL_DB_PATH", env_values, BASE_DIR / "resources" / "dictionaries" / "cor.sqlite")
        ),
        word_verification_enabled=_required_env("DANOTE_WORD_VERIFICATION_ENABLED", env_values, "1").lower()
        not in {"0", "false", "no"},
        word_verification_gemini_api_key=_required_or_optional_env(
            "DANOTE_WORD_VERIFICATION_GEMINI_API_KEY",
            env_values,
            _optional_env("DANOTE_GEMINI_API_KEY", env_values),
        ),
        word_verification_gemini_model=_required_env(
            "DANOTE_WORD_VERIFICATION_GEMINI_MODEL",
            env_values,
            _required_env("DANOTE_GEMINI_MODEL", env_values, "gemini-3.1-flash-lite-preview"),
        ),
        tts_enabled=_required_env("DANOTE_TTS_ENABLED", env_values, "1").lower() not in {"0", "false", "no"},
        tts_provider=_required_env("DANOTE_TTS_PROVIDER", env_values, "azure"),
        tts_azure_api_key=_optional_env("DANOTE_TTS_AZURE_API_KEY", env_values),
        tts_azure_region=_optional_env("DANOTE_TTS_AZURE_REGION", env_values),
        tts_azure_endpoint=_optional_env("DANOTE_TTS_AZURE_ENDPOINT", env_values),
        tts_azure_voice_name=_required_env("DANOTE_TTS_AZURE_VOICE_NAME", env_values, "da-DK-ChristelNeural"),
        gemini_changes_log_path=Path(
            _required_env("DANOTE_GEMINI_CHANGES_LOG_PATH", env_values, DATA_DIR / "gemini-applied-changes.jsonl")
        ),
    )


def _load_env_file(path: Path) -> dict[str, str]:
    loaded: dict[str, str] = {}
    if not path.exists():
        return loaded

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        normalized_key = key.strip()
        if not normalized_key:
            continue
        loaded[normalized_key] = _normalize_env_value(value.strip())
    return loaded


def _normalize_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _required_env(name: str, env_values: dict[str, str], default: str | Path) -> str:
    value = os.getenv(name)
    if value is not None:
        return value
    if name in env_values:
        return env_values[name]
    return str(default)


def _optional_env(name: str, env_values: dict[str, str]) -> str | None:
    value = os.getenv(name)
    if value is not None:
        return value
    return env_values.get(name)


def _required_or_optional_env(name: str, env_values: dict[str, str], default: str | None) -> str | None:
    value = os.getenv(name)
    if value is not None:
        return value
    if name in env_values:
        return env_values[name]
    return default
