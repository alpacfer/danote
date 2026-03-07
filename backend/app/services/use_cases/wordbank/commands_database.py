from __future__ import annotations

import os

from app.api.schemas.v1.wordbank import ResetDatabaseResponse
from app.db.migrations import apply_migrations
from app.services.use_cases.wordbank.runtime import WordbankRuntime


def reset_database(runtime: WordbankRuntime) -> ResetDatabaseResponse:
    if runtime.db_path.exists():
        os.remove(runtime.db_path)
    apply_migrations(runtime.db_path)
    runtime.nlp.invalidate_typo_cache()
    return ResetDatabaseResponse(
        status="reset",
        message="Database reset complete.",
    )
