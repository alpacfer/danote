from __future__ import annotations

import logging
import sqlite3

from fastapi import APIRouter, HTTPException, Request

from app.api.schemas.v1.wordbank import (
    AddWordRequest,
    AddWordResponse,
    GeneratePhraseTranslationRequest,
    GeneratePhraseTranslationResponse,
    GenerateTranslationRequest,
    GenerateTranslationResponse,
    LemmaDetailsResponse,
    LemmaListResponse,
    ResetDatabaseResponse,
)
from app.services.use_cases import WordbankUseCase

router = APIRouter()
logger = logging.getLogger(__name__)


def _require_db_ready(request: Request) -> None:
    if not bool(getattr(request.app.state, "db_ready", False)):
        raise HTTPException(
            status_code=503,
            detail="Database unavailable. Check backend logs and DB path configuration.",
        )


def _wordbank_use_case(request: Request) -> WordbankUseCase:
    return WordbankUseCase(
        db_path=request.app.state.settings.db_path,
        typo_engine=getattr(request.app.state, "typo_engine", None),
        translation_service=getattr(request.app.state, "translation_service", None),
    )


@router.post("/wordbank/lexemes", response_model=AddWordResponse)
def add_word(payload: AddWordRequest, request: Request) -> AddWordResponse:
    _require_db_ready(request)

    try:
        return _wordbank_use_case(request).add_word(payload.surface_token, payload.lemma_candidate)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except sqlite3.OperationalError as exc:
        logger.exception("wordbank_db_operational_error")
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc}",
        ) from exc


@router.post("/wordbank/translation", response_model=GenerateTranslationResponse)
def generate_translation(payload: GenerateTranslationRequest, request: Request) -> GenerateTranslationResponse:
    _require_db_ready(request)

    try:
        return _wordbank_use_case(request).generate_translation(payload.surface_token, payload.lemma_candidate)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except sqlite3.OperationalError as exc:
        logger.exception("wordbank_db_operational_error")
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc}",
        ) from exc


@router.post("/wordbank/phrase-translation", response_model=GeneratePhraseTranslationResponse)
def generate_phrase_translation(
    payload: GeneratePhraseTranslationRequest,
    request: Request,
) -> GeneratePhraseTranslationResponse:
    _require_db_ready(request)

    try:
        return _wordbank_use_case(request).generate_phrase_translation(payload.source_text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except sqlite3.OperationalError as exc:
        logger.exception("wordbank_db_operational_error")
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc}",
        ) from exc


@router.get("/wordbank/lemmas", response_model=LemmaListResponse)
def list_lemmas(request: Request) -> LemmaListResponse:
    _require_db_ready(request)

    try:
        return _wordbank_use_case(request).list_lemmas()
    except sqlite3.OperationalError as exc:
        logger.exception("wordbank_db_operational_error")
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc}",
        ) from exc


@router.get("/wordbank/lemmas/{lemma}", response_model=LemmaDetailsResponse)
def get_lemma_details(lemma: str, request: Request) -> LemmaDetailsResponse:
    _require_db_ready(request)

    try:
        return _wordbank_use_case(request).get_lemma_details(lemma)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except sqlite3.OperationalError as exc:
        logger.exception("wordbank_db_operational_error")
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc}",
        ) from exc


@router.delete("/wordbank/database", response_model=ResetDatabaseResponse)
def reset_database(request: Request) -> ResetDatabaseResponse:
    _require_db_ready(request)

    try:
        response = _wordbank_use_case(request).reset_database()
        request.app.state.db_ready = True
        request.app.state.db_error = None
        return response
    except OSError as exc:
        logger.exception("wordbank_db_reset_os_error")
        raise HTTPException(
            status_code=503,
            detail=f"Database reset failed: {exc}",
        ) from exc
    except sqlite3.OperationalError as exc:
        logger.exception("wordbank_db_reset_operational_error")
        raise HTTPException(
            status_code=503,
            detail=f"Database reset failed: {exc}",
        ) from exc
