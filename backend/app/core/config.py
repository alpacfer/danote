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
        nlp_model=os.getenv("DANOTE_NLP_MODEL", "da_dacy_small_tft-0.0.0"),
        cors_origins=parsed_cors_origins or DEFAULT_CORS_ORIGINS,
        typo_enabled=os.getenv("DANOTE_TYPO_ENABLED", "1").lower() not in {"0", "false", "no"},
        typo_dictionary_path=Path(os.getenv("DANOTE_TYPO_DICTIONARY_PATH"))
        if os.getenv("DANOTE_TYPO_DICTIONARY_PATH")
        else None,
        translation_enabled=os.getenv("DANOTE_TRANSLATION_ENABLED", "1").lower()
        not in {"0", "false", "no"},
    )
