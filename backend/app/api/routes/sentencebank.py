from __future__ import annotations

import logging
import sqlite3

from fastapi import APIRouter, HTTPException, Request

from app.api.schemas.v1.sentencebank import (
    AddSentenceRequest,
    AddSentenceResponse,
    SentenceListResponse,
)
from app.services.use_cases import SentencebankUseCase

router = APIRouter()
logger = logging.getLogger(__name__)


def _require_db_ready(request: Request) -> None:
    if not bool(getattr(request.app.state, "db_ready", False)):
        raise HTTPException(
            status_code=503,
            detail="Database unavailable. Check backend logs and DB path configuration.",
        )


def _sentencebank_use_case(request: Request) -> SentencebankUseCase:
    return SentencebankUseCase(
        db_path=request.app.state.settings.db_path,
        translation_service=getattr(request.app.state, "translation_service", None),
    )


@router.post("/sentencebank/sentences", response_model=AddSentenceResponse)
def add_sentence(payload: AddSentenceRequest, request: Request) -> AddSentenceResponse:
    _require_db_ready(request)

    try:
        return _sentencebank_use_case(request).add_sentence(payload.source_text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except sqlite3.OperationalError as exc:
        logger.exception("sentencebank_db_operational_error")
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc}",
        ) from exc


@router.get("/sentencebank/sentences", response_model=SentenceListResponse)
def list_sentences(request: Request) -> SentenceListResponse:
    _require_db_ready(request)

    try:
        return _sentencebank_use_case(request).list_sentences()
    except sqlite3.OperationalError as exc:
        logger.exception("sentencebank_db_operational_error")
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc}",
        ) from exc
