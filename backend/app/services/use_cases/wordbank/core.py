from __future__ import annotations

from pathlib import Path

from app.nlp.adapter import NLPAdapter
from app.services.cor import CORLexiconService
from app.services.cor_local import CORLocalLexiconService
from app.services.translation import TranslationService
from app.services.tts import TTSService
from app.services.use_cases.wordbank.commands import WordbankCommandsMixin
from app.services.use_cases.wordbank.cor_resolution import WordbankCorResolutionMixin
from app.services.use_cases.wordbank.queries import WordbankQueriesMixin
from app.services.use_cases.wordbank.translation_pronunciation import WordbankTranslationPronunciationMixin
from app.services.use_cases.wordbank.verification import WordbankVerificationMixin
from app.services.verification import WordVerificationService


class WordbankUseCase(
    WordbankCommandsMixin,
    WordbankQueriesMixin,
    WordbankCorResolutionMixin,
    WordbankTranslationPronunciationMixin,
    WordbankVerificationMixin,
):
    _AMBIGUOUS_SHORT_WORDS = frozenset(
        {
            "an",
            "at",
            "de",
            "den",
            "det",
            "en",
            "for",
            "gift",
            "i",
            "in",
            "is",
            "it",
            "to",
        }
    )

    def __init__(
        self,
        db_path,
        typo_engine=None,
        translation_service: TranslationService | None = None,
        nlp_adapter: NLPAdapter | None = None,
        cor_lexicon_service: CORLexiconService | None = None,
        cor_local_lexicon_service: CORLocalLexiconService | None = None,
        verification_service: WordVerificationService | None = None,
        tts_service: TTSService | None = None,
        gemini_changes_log_path: Path | None = None,
    ):
        self._db_path = db_path
        self._typo_engine = typo_engine
        self._translation_service = translation_service
        self._nlp_adapter = nlp_adapter
        self._cor_lexicon_service = cor_lexicon_service
        self._cor_local_lexicon_service = cor_local_lexicon_service
        self._verification_service = verification_service
        self._tts_service = tts_service
        self._gemini_changes_log_path = gemini_changes_log_path
        self._pos_morph_cache: dict[tuple[str, str | None], tuple[str | None, str | None]] = {}
