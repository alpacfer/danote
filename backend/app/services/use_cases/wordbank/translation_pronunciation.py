from __future__ import annotations

from app.services.use_cases.wordbank.pronunciation_audio import WordbankPronunciationAudioMixin
from app.services.use_cases.wordbank.translation_detection import WordbankTranslationDetectionMixin


class WordbankTranslationPronunciationMixin(
    WordbankTranslationDetectionMixin,
    WordbankPronunciationAudioMixin,
):
    pass
