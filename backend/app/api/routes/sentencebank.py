from __future__ import annotations

import logging

from fastapi import APIRouter, Request

from app.api.routes._runtime import get_services, get_settings, run_db_operation
from app.api.schemas.v1.sentencebank import (
    AddSentenceRequest,
    AddSentenceResponse,
    SentenceListResponse,
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
    )


@router.post("/sentencebank/sentences", response_model=AddSentenceResponse)
def add_sentence(payload: AddSentenceRequest, request: Request) -> AddSentenceResponse:
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
