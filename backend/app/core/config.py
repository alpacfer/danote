from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"


@dataclass(frozen=True)
class Settings:
    environment: str
    app_name: str
    host: str
    port: int
    db_path: Path
    nlp_model: str



def load_settings() -> Settings:
    db_path = Path(os.getenv("DANOTE_DB_PATH", DATA_DIR / "danote.sqlite3"))
    return Settings(
        environment=os.getenv("DANOTE_ENV", "development"),
        app_name=os.getenv("DANOTE_APP_NAME", "danote-backend"),
        host=os.getenv("DANOTE_HOST", "127.0.0.1"),
        port=int(os.getenv("DANOTE_PORT", "8000")),
        db_path=db_path,
        nlp_model=os.getenv("DANOTE_NLP_MODEL", "da_dacy_small_tft-0.0.0"),
    )
