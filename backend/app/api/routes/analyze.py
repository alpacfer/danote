from __future__ import annotations

import logging
import sqlite3

from fastapi import APIRouter, HTTPException, Request

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
    if not bool(getattr(request.app.state, "db_ready", False)):
        raise HTTPException(
            status_code=503,
            detail="Database unavailable. Check backend logs and DB path configuration.",
        )
    if not bool(getattr(request.app.state, "nlp_ready", False)):
        raise HTTPException(
            status_code=503,
            detail="NLP unavailable. Check backend logs and NLP model installation.",
        )

    settings = request.app.state.settings
    nlp_adapter = request.app.state.nlp_adapter
    if nlp_adapter is None:
        raise HTTPException(
            status_code=503,
            detail="NLP unavailable. Check backend logs and NLP model installation.",
        )

    use_case = AnalyzeNoteUseCase(
        settings.db_path,
        nlp_adapter=nlp_adapter,
        typo_engine=getattr(request.app.state, "typo_engine", None),
    )

    try:
        tokens = use_case.execute(payload.text)
    except sqlite3.OperationalError as exc:
        logger.exception("analyze_db_operational_error")
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc}",
        ) from exc

    return AnalyzeResponse(tokens=tokens)


@router.post("/analyze/enrich-token", response_model=ResolveQueryResponse)
def enrich_token(payload: EnrichTokenRequest, request: Request) -> ResolveQueryResponse:
    if not bool(getattr(request.app.state, "db_ready", False)):
        raise HTTPException(
            status_code=503,
            detail="Database unavailable. Check backend logs and DB path configuration.",
        )

    use_case = build_wordbank_use_case(request)

    try:
        return use_case.resolve_query(
            payload.token,
            include_translations=payload.include_translations,
            include_language_detection=payload.include_language_detection,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except sqlite3.OperationalError as exc:
        logger.exception("analyze_enrich_token_db_operational_error")
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc}",
        ) from exc
