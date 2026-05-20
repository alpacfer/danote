from __future__ import annotations

from fastapi import Request

from app.api.auth import require_current_user
from app.api.routes._runtime import (
    get_runtime_state,
    get_settings,
    resolve_services_for_user,
)
from app.services.use_cases import TrialUseCase, WordbankUseCase
from app.services.use_cases.account import AccountUseCase


def build_wordbank_use_case(request: Request) -> WordbankUseCase:
    settings = get_settings(request)
    current_user = require_current_user(request)
    services = resolve_services_for_user(request, current_user.id)
    return WordbankUseCase(
        db_path=settings.db_path,
        owner_user_id=current_user.id,
        translation_service=services.translation_service,
        gemini_word_translation_service=services.gemini_word_translation_service,
        gemini_related_words_service=services.gemini_related_words_service,
        nlp_adapter=services.nlp_adapter,
        cor_lexicon_service=services.cor_lexicon_service,
        cor_local_lexicon_service=services.cor_local_lexicon_service,
        en_local_lexicon_service=services.en_local_lexicon_service,
        en_gemini_translation_service=services.en_gemini_translation_service,
        verification_service=services.word_verification_service,
        tts_service=services.tts_service,
        gemini_changes_log_path=settings.gemini_changes_log_path,
    )


def build_trial_use_case(request: Request) -> TrialUseCase:
    runtime = get_runtime_state(request)
    settings = runtime.settings
    trial_repo = runtime.user_trial_repository
    if trial_repo is None:
        raise RuntimeError("trial repository is not initialized")
    return TrialUseCase(
        settings=settings,
        trial_repository=trial_repo,
        api_keys_repository=runtime.user_api_keys_repository,
    )


def build_account_use_case(request: Request) -> AccountUseCase:
    runtime = get_runtime_state(request)
    return AccountUseCase(
        db_path=runtime.settings.db_path,
        api_keys_repository=runtime.user_api_keys_repository,
        trial_use_case=build_trial_use_case(request),
    )
