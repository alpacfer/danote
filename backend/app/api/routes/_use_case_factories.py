from __future__ import annotations

from fastapi import Request

from app.api.routes._runtime import get_services, get_settings
from app.services.use_cases import WordbankUseCase


def build_wordbank_use_case(request: Request) -> WordbankUseCase:
    settings = get_settings(request)
    services = get_services(request)
    return WordbankUseCase(
        db_path=settings.db_path,
        typo_engine=services.typo_engine,
        translation_service=services.translation_service,
        nlp_adapter=services.nlp_adapter,
        cor_lexicon_service=services.cor_lexicon_service,
        cor_local_lexicon_service=services.cor_local_lexicon_service,
        verification_service=services.word_verification_service,
        tts_service=services.tts_service,
        gemini_changes_log_path=settings.gemini_changes_log_path,
    )
