from __future__ import annotations

from fastapi import Request

from app.services.use_cases import WordbankUseCase


def build_wordbank_use_case(request: Request) -> WordbankUseCase:
    return WordbankUseCase(
        db_path=request.app.state.settings.db_path,
        typo_engine=getattr(request.app.state, "typo_engine", None),
        translation_service=getattr(request.app.state, "translation_service", None),
        nlp_adapter=getattr(request.app.state, "nlp_adapter", None),
        cor_lexicon_service=getattr(request.app.state, "cor_lexicon_service", None),
        verification_service=getattr(request.app.state, "word_verification_service", None),
        tts_service=getattr(request.app.state, "tts_service", None),
        gemini_changes_log_path=request.app.state.settings.gemini_changes_log_path,
    )
