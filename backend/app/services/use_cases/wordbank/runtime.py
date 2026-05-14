from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.db.repositories import WordbankRepository
from app.services.use_cases.wordbank.collaborators.cor import CorResolutionCollaborator
from app.services.use_cases.wordbank.collaborators.nlp import NLPCollaborator
from app.services.use_cases.wordbank.collaborators.pronunciation import PronunciationCollaborator
from app.services.use_cases.wordbank.collaborators.related_words import RelatedWordsCollaborator
from app.services.use_cases.wordbank.collaborators.translation import TranslationCollaborator
from app.services.use_cases.wordbank.collaborators.verification import VerificationCollaborator


@dataclass(frozen=True, slots=True)
class WordbankRuntime:
    db_path: Path
    owner_user_id: int
    repository: WordbankRepository
    nlp: NLPCollaborator
    pronunciation: PronunciationCollaborator
    related_words: RelatedWordsCollaborator
    translation: TranslationCollaborator
    cor: CorResolutionCollaborator
    verification: VerificationCollaborator
