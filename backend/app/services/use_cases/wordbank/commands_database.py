from __future__ import annotations

from app.api.schemas.v1.wordbank import ResetDatabaseResponse
from app.services.use_cases.user_data_reset import clear_user_learning_data
from app.services.use_cases.wordbank.runtime import WordbankRuntime


def reset_database(runtime: WordbankRuntime) -> ResetDatabaseResponse:
    clear_user_learning_data(runtime.db_path, runtime.owner_user_id, include_search_usage=True)
    runtime.nlp.invalidate_typo_cache()
    return ResetDatabaseResponse(
        status="reset",
        message="Database reset complete.",
    )
