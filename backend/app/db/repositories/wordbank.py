from __future__ import annotations

from pathlib import Path

from app.db.repositories.wordbank_category_mutations import WordbankCategoryMutationRepository
from app.db.repositories.wordbank_category_reads import WordbankCategoryReadRepository
from app.db.repositories.wordbank_models import (
    AdditionalTranslationRecord,
    LemmaListRow,
    LexemeMeaningRecord,
    LexemeRecord,
    RelatedWordRecord,
    RelatedWordWriteRecord,
    SavedWordbankTargetRecord,
    SavedTranslationTargetRecord,
    SurfaceFormRecord,
    VerificationRecord,
    WordbankSearchRow,
    WordCategoryAssignmentRecord,
    WordCategoryRecord,
)
from app.db.repositories.wordbank_mutations import WordbankMutationRepository
from app.db.repositories.wordbank_reads import WordbankReadRepository


class WordbankRepository(
    WordbankCategoryReadRepository,
    WordbankCategoryMutationRepository,
    WordbankReadRepository,
    WordbankMutationRepository,
):
    """Stable public façade combining read/query and mutation/upsert repositories."""

    def __init__(self, db_path: Path):
        self._db_path = db_path


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
    "VerificationRecord",
    "WordCategoryRecord",
    "WordCategoryAssignmentRecord",
    "WordbankRepository",
]
