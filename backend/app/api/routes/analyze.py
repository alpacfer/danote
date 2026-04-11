from __future__ import annotations

import logging

from fastapi import APIRouter, Request

from app.api.routes._runtime import get_services, get_settings, require_nlp_ready, run_db_operation
from app.api.routes._use_case_factories import build_wordbank_use_case
from app.api.schemas.v1.analyze import (
    AnalyzeRequest,
    AnalyzeResponse,
    EnrichTokenRequest,
)
from app.api.schemas.v1.wordbank import ResolveQueryResponse
from app.services.use_cases import AnalyzeNoteUseCase

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze_note(payload: AnalyzeRequest, request: Request) -> AnalyzeResponse:
    require_nlp_ready(request)
    settings = get_settings(request)
    services = get_services(request)

    use_case = AnalyzeNoteUseCase(
        settings.db_path,
        nlp_adapter=services.nlp_adapter,
    )

    tokens = run_db_operation(
        request,
        lambda: use_case.execute(payload.text),
        error_log_name="analyze_db_operational_error",
    )

    return AnalyzeResponse(tokens=tokens)


@router.post("/analyze/enrich-token", response_model=ResolveQueryResponse)
def enrich_token(payload: EnrichTokenRequest, request: Request) -> ResolveQueryResponse:
    use_case = build_wordbank_use_case(request)
    return run_db_operation(
        request,
        lambda: use_case.resolve_query(
            payload.token,
            include_translations=payload.include_translations,
            include_language_detection=payload.include_language_detection,
        ),
        error_log_name="analyze_enrich_token_db_operational_error",
    )
