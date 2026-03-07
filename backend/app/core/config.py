from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
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


def load_settings() -> Settings:
    db_path = Path(os.getenv("DANOTE_DB_PATH", DATA_DIR / "danote.sqlite3"))
    typo_dictionary_path = os.getenv("DANOTE_TYPO_DICTIONARY_PATH")
    raw_cors_origins = os.getenv("DANOTE_CORS_ORIGINS", "")
    parsed_cors_origins = tuple(
        origin.strip()
        for origin in raw_cors_origins.split(",")
        if origin.strip()
    )
    return Settings(
        environment=os.getenv("DANOTE_ENV", "development"),
        app_name=os.getenv("DANOTE_APP_NAME", "danote-backend"),
        host=os.getenv("DANOTE_HOST", "127.0.0.1"),
        port=int(os.getenv("DANOTE_PORT", "8000")),
        db_path=db_path,
        nlp_model=os.getenv("DANOTE_NLP_MODEL", "da_dacy_small_trf-0.2.0"),
        nlp_enabled=os.getenv("DANOTE_NLP_ENABLED", "1").lower() not in {"0", "false", "no"},
        cors_origins=parsed_cors_origins or DEFAULT_CORS_ORIGINS,
        typo_enabled=os.getenv("DANOTE_TYPO_ENABLED", "1").lower() not in {"0", "false", "no"},
        typo_dictionary_path=Path(typo_dictionary_path) if typo_dictionary_path else None,
        translation_enabled=os.getenv("DANOTE_TRANSLATION_ENABLED", "1").lower()
        not in {"0", "false", "no"},
        translation_provider=os.getenv("DANOTE_TRANSLATION_PROVIDER", "azure"),
        translation_azure_api_key=os.getenv("DANOTE_TRANSLATION_AZURE_API_KEY"),
        translation_azure_region=os.getenv("DANOTE_TRANSLATION_AZURE_REGION"),
        translation_azure_endpoint=os.getenv("DANOTE_TRANSLATION_AZURE_ENDPOINT"),
        translation_azure_api_version=os.getenv("DANOTE_TRANSLATION_AZURE_API_VERSION", "3.0"),
        cor_lookup_enabled=os.getenv("DANOTE_COR_LOOKUP_ENABLED", "1").lower() not in {"0", "false", "no"},
        cor_lookup_timeout_seconds=float(os.getenv("DANOTE_COR_LOOKUP_TIMEOUT_SECONDS", "4.0")),
        cor_local_db_path=Path(
            os.getenv("DANOTE_COR_LOCAL_DB_PATH", BASE_DIR / "resources" / "dictionaries" / "cor.sqlite")
        ),
        word_verification_enabled=os.getenv("DANOTE_WORD_VERIFICATION_ENABLED", "1").lower()
        not in {"0", "false", "no"},
        word_verification_gemini_api_key=os.getenv(
            "DANOTE_WORD_VERIFICATION_GEMINI_API_KEY",
            os.getenv("DANOTE_GEMINI_API_KEY"),
        ),
        word_verification_gemini_model=os.getenv(
            "DANOTE_WORD_VERIFICATION_GEMINI_MODEL",
            os.getenv("DANOTE_GEMINI_MODEL", "gemini-3-flash-preview"),
        ),
        tts_enabled=os.getenv("DANOTE_TTS_ENABLED", "1").lower() not in {"0", "false", "no"},
        tts_provider=os.getenv("DANOTE_TTS_PROVIDER", "azure"),
        tts_azure_api_key=os.getenv("DANOTE_TTS_AZURE_API_KEY"),
        tts_azure_region=os.getenv("DANOTE_TTS_AZURE_REGION"),
        tts_azure_endpoint=os.getenv("DANOTE_TTS_AZURE_ENDPOINT"),
        tts_azure_voice_name=os.getenv("DANOTE_TTS_AZURE_VOICE_NAME", "da-DK-ChristelNeural"),
        gemini_changes_log_path=Path(
            os.getenv("DANOTE_GEMINI_CHANGES_LOG_PATH", DATA_DIR / "gemini-applied-changes.jsonl")
        ),
    )
