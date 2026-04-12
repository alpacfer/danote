from __future__ import annotations

import logging

from fastapi import APIRouter, Request

from app.api.routes._runtime import (
    get_services,
    get_settings,
    require_nlp_ready,
    run_db_operation,
)
from app.api.routes._use_case_factories import build_wordbank_use_case
from app.api.schemas.v1.sentencebank import (
    AddSentenceRequest,
    AddSentenceResponse,
    SentenceListResponse,
    VerifySentenceRequest,
    VerifySentenceResponse,
)
from app.services.use_cases import SentencebankUseCase

router = APIRouter()
logger = logging.getLogger(__name__)


def _sentencebank_use_case(request: Request) -> SentencebankUseCase:
    settings = get_settings(request)
    services = get_services(request)
    return SentencebankUseCase(
        db_path=settings.db_path,
        translation_service=services.translation_service,
        nlp_adapter=services.nlp_adapter,
        wordbank_use_case=build_wordbank_use_case(request),
        sentence_verification_service=services.sentence_verification_service,
    )


@router.post("/sentencebank/sentences", response_model=AddSentenceResponse)
def add_sentence(payload: AddSentenceRequest, request: Request) -> AddSentenceResponse:
    require_nlp_ready(request)
    return run_db_operation(
        request,
        lambda: _sentencebank_use_case(request).add_sentence(payload.source_text),
        error_log_name="sentencebank_db_operational_error",
    )


@router.get("/sentencebank/sentences", response_model=SentenceListResponse)
def list_sentences(request: Request) -> SentenceListResponse:
    return run_db_operation(
        request,
        lambda: _sentencebank_use_case(request).list_sentences(),
        error_log_name="sentencebank_db_operational_error",
    )


@router.post("/sentencebank/verify-sentence", response_model=VerifySentenceResponse)
def verify_sentence(payload: VerifySentenceRequest, request: Request) -> VerifySentenceResponse:
    return run_db_operation(
        request,
        lambda: _sentencebank_use_case(request).verify_sentence(payload.source_text),
        error_log_name="sentencebank_verify_db_operational_error",
    )
