from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


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
    cors_origins: tuple[str, ...] = DEFAULT_CORS_ORIGINS
    typo_enabled: bool = True
    typo_dictionary_path: Path | None = None
    translation_enabled: bool = True
    translation_provider: str = "deepl"
    translation_gemini_api_key: str | None = None
    translation_gemini_model: str = "gemini-3-flash-preview"
    translation_deepl_api_key: str | None = None
    translation_deepl_api_url: str | None = None
    word_verification_enabled: bool = False
    word_verification_gemini_api_key: str | None = None
    word_verification_gemini_model: str = "gemini-3-flash-preview"


def load_settings() -> Settings:
    db_path = Path(os.getenv("DANOTE_DB_PATH", DATA_DIR / "danote.sqlite3"))
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
        cors_origins=parsed_cors_origins or DEFAULT_CORS_ORIGINS,
        typo_enabled=os.getenv("DANOTE_TYPO_ENABLED", "1").lower() not in {"0", "false", "no"},
        typo_dictionary_path=Path(os.getenv("DANOTE_TYPO_DICTIONARY_PATH"))
        if os.getenv("DANOTE_TYPO_DICTIONARY_PATH")
        else None,
        translation_enabled=os.getenv("DANOTE_TRANSLATION_ENABLED", "1").lower()
        not in {"0", "false", "no"},
        translation_provider=os.getenv("DANOTE_TRANSLATION_PROVIDER", "deepl"),
        translation_gemini_api_key=os.getenv("DANOTE_GEMINI_API_KEY", "AIzaSyCTDgy8kmCa4UB0KH8xfXeK4ToNOjLwlMI"),
        translation_gemini_model=os.getenv("DANOTE_GEMINI_MODEL", "gemini-3-flash-preview"),
        translation_deepl_api_key=os.getenv("DANOTE_DEEPL_API_KEY", "4f853833-6289-42af-86ca-3171a46e05d6:fx"),
        translation_deepl_api_url=os.getenv("DANOTE_DEEPL_API_URL"),
        word_verification_enabled=os.getenv("DANOTE_WORD_VERIFICATION_ENABLED", "1").lower()
        not in {"0", "false", "no"},
        word_verification_gemini_api_key=os.getenv(
            "DANOTE_WORD_VERIFICATION_GEMINI_API_KEY",
            os.getenv("DANOTE_GEMINI_API_KEY", "AIzaSyCTDgy8kmCa4UB0KH8xfXeK4ToNOjLwlMI"),
        ),
        word_verification_gemini_model=os.getenv(
            "DANOTE_WORD_VERIFICATION_GEMINI_MODEL",
            os.getenv("DANOTE_GEMINI_MODEL", "gemini-3-flash-preview"),
        ),
    )
