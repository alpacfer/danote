from __future__ import annotations

from pathlib import Path

from app.db.repositories.wordbank_category_mutations import WordbankCategoryMutationRepository
from app.db.repositories.wordbank_category_reads import WordbankCategoryReadRepository
from app.db.repositories.wordbank_change_log import WordbankChangeLogRepository
from app.db.repositories.wordbank_models import (
    AdditionalTranslationRecord,
    LemmaListRow,
    LexemeMeaningRecord,
    LexemeRecord,
    RelatedWordRecord,
    RelatedWordWriteRecord,
    SavedTranslationTargetRecord,
    SavedWordbankTargetRecord,
    SurfaceFormRecord,
    VerificationChangeLogRecord,
    VerificationRecord,
    WordbankSearchRow,
    WordCategoryAssignmentRecord,
    WordCategoryRecord,
)
from app.db.repositories.wordbank_mutations import WordbankMutationRepository
from app.db.repositories.wordbank_reads import WordbankReadRepository


class WordbankRepository(
    WordbankChangeLogRepository,
    WordbankCategoryReadRepository,
    WordbankCategoryMutationRepository,
    WordbankReadRepository,
    WordbankMutationRepository,
):
    """Stable public façade combining read/query and mutation/upsert repositories."""

    def __init__(self, db_path: Path, *, owner_user_id: int = 1):
        self._db_path = db_path
        self._owner_user_id = owner_user_id


__all__ = [
    "LemmaListRow",
    "WordbankSearchRow",
    "LexemeRecord",
    "LexemeMeaningRecord",
    "SurfaceFormRecord",
    "AdditionalTranslationRecord",
    "RelatedWordRecord",
    "RelatedWordWriteRecord",
    "SavedWordbankTargetRecord",
    "SavedTranslationTargetRecord",
    "VerificationChangeLogRecord",
    "VerificationRecord",
    "WordCategoryRecord",
    "WordCategoryAssignmentRecord",
    "WordbankChangeLogRepository",
    "WordbankRepository",
]
