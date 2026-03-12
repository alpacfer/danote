from __future__ import annotations

from pathlib import Path

from app.db.repositories.wordbank_models import (
    LemmaListRow,
    LexemeMeaningRecord,
    LexemeRecord,
    SurfaceFormRecord,
    WordbankSearchRow,
)
from app.db.repositories.wordbank_mutations import WordbankMutationRepository
from app.db.repositories.wordbank_reads import WordbankReadRepository


class WordbankRepository(WordbankReadRepository, WordbankMutationRepository):
    """Stable public façade combining read/query and mutation/upsert repositories."""

    def __init__(self, db_path: Path):
        self._db_path = db_path


__all__ = [
    "LemmaListRow",
    "WordbankSearchRow",
    "LexemeRecord",
    "LexemeMeaningRecord",
    "SurfaceFormRecord",
    "WordbankRepository",
]
