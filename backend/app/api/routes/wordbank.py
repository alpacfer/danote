from __future__ import annotations

import logging
import sqlite3

from fastapi import APIRouter, HTTPException, Query, Request, Response

from app.api.routes._use_case_factories import build_wordbank_use_case
from app.api.schemas.v1.wordbank import (
    AddWordRequest,
    AddWordResponse,
    ApplyVerificationChangesRequest,
    ApplyVerificationChangesResponse,
    CORLemmaParadigmResponse,
    CORSearchFormResponse,
    DetectWordLanguageRequest,
    DetectWordLanguageResponse,
    GeneratePronunciationRequest,
    GeneratePronunciationResponse,
    GeneratePhraseTranslationRequest,
    GeneratePhraseTranslationResponse,
    GenerateReverseTranslationRequest,
    GenerateReverseTranslationResponse,
    GenerateTranslationRequest,
    GenerateTranslationResponse,
    LemmaDetailsResponse,
    LemmaListResponse,
    ResetDatabaseResponse,
    ResolveQueryRequest,
    ResolveQueryResponse,
    VerifyWordRequest,
    VerifyWordResponse,
    WordbankSearchResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def _require_db_ready(request: Request) -> None:
    if not bool(getattr(request.app.state, "db_ready", False)):
        raise HTTPException(
            status_code=503,
            detail="Database unavailable. Check backend logs and DB path configuration.",
        )



@router.post("/wordbank/lexemes", response_model=AddWordResponse)
def add_word(payload: AddWordRequest, request: Request) -> AddWordResponse:
    _require_db_ready(request)

    try:
        return build_wordbank_use_case(request).add_word(
            payload.surface_token,
            payload.lemma_candidate,
            pos_tag=payload.pos_tag,
            morphology=payload.morphology,
        )
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


@router.post("/wordbank/lexemes/verify", response_model=VerifyWordResponse)
def verify_added_word(payload: VerifyWordRequest, request: Request) -> VerifyWordResponse:
    _require_db_ready(request)

    try:
        return build_wordbank_use_case(request).verify_added_word(payload.stored_lemma, payload.stored_surface_form)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except sqlite3.OperationalError as exc:
        logger.exception("wordbank_db_operational_error")
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc}",
        ) from exc


@router.post("/wordbank/lexemes/pronunciation", response_model=GeneratePronunciationResponse)
def generate_pronunciation(
    payload: GeneratePronunciationRequest,
    request: Request,
) -> GeneratePronunciationResponse:
    _require_db_ready(request)

    try:
        return build_wordbank_use_case(request).generate_pronunciation_for_added_word(
            payload.stored_lemma,
            payload.stored_surface_form,
            force=payload.force,
        )
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


@router.post("/wordbank/lexemes/apply-verification-changes", response_model=ApplyVerificationChangesResponse)
def apply_verification_changes(
    payload: ApplyVerificationChangesRequest,
    request: Request,
) -> ApplyVerificationChangesResponse:
    _require_db_ready(request)

    try:
        return build_wordbank_use_case(request).apply_verification_changes(
            stored_lemma=payload.stored_lemma,
            stored_surface_form=payload.stored_surface_form,
            suggested_changes=payload.suggested_changes.model_dump(),
            provider=payload.provider,
        )
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


@router.post("/wordbank/translation", response_model=GenerateTranslationResponse)
def generate_translation(payload: GenerateTranslationRequest, request: Request) -> GenerateTranslationResponse:
    _require_db_ready(request)

    try:
        return build_wordbank_use_case(request).generate_translation(payload.surface_token, payload.lemma_candidate)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except sqlite3.OperationalError as exc:
        logger.exception("wordbank_db_operational_error")
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc}",
        ) from exc


@router.post("/wordbank/reverse-translation", response_model=GenerateReverseTranslationResponse)
def generate_reverse_translation(
    payload: GenerateReverseTranslationRequest,
    request: Request,
) -> GenerateReverseTranslationResponse:
    _require_db_ready(request)

    try:
        return build_wordbank_use_case(request).generate_reverse_translation(payload.source_word)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except sqlite3.OperationalError as exc:
        logger.exception("wordbank_db_operational_error")
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc}",
        ) from exc


@router.post("/wordbank/detect-language", response_model=DetectWordLanguageResponse)
def detect_word_language(
    payload: DetectWordLanguageRequest,
    request: Request,
) -> DetectWordLanguageResponse:
    _require_db_ready(request)

    try:
        return build_wordbank_use_case(request).detect_word_language(payload.source_word)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except sqlite3.OperationalError as exc:
        logger.exception("wordbank_db_operational_error")
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc}",
        ) from exc




@router.post("/wordbank/resolve-query", response_model=ResolveQueryResponse)
def resolve_query(payload: ResolveQueryRequest, request: Request) -> ResolveQueryResponse:
    _require_db_ready(request)

    try:
        return build_wordbank_use_case(request).resolve_query(
            payload.query_text,
            include_translations=payload.include_translations,
            include_language_detection=payload.include_language_detection,
        )
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
        return build_wordbank_use_case(request).generate_phrase_translation(payload.source_text)
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
        return build_wordbank_use_case(request).list_lemmas()
    except sqlite3.OperationalError as exc:
        logger.exception("wordbank_db_operational_error")
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc}",
        ) from exc


@router.get("/wordbank/search", response_model=WordbankSearchResponse)
def search_wordbank(
    request: Request,
    query: str = Query(..., min_length=1),
    limit: int = Query(8, ge=1, le=50),
) -> WordbankSearchResponse:
    _require_db_ready(request)

    try:
        return build_wordbank_use_case(request).search_lemmas(query, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except sqlite3.OperationalError as exc:
        logger.exception("wordbank_db_operational_error")
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc}",
        ) from exc


@router.get("/wordbank/search/cor-form", response_model=CORSearchFormResponse)
def search_cor_form(
    request: Request,
    form: str = Query(..., min_length=1),
    limit: int = Query(100, ge=1, le=500),
) -> CORSearchFormResponse:
    _require_db_ready(request)

    try:
        return build_wordbank_use_case(request).search_cor_form(form, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except sqlite3.OperationalError as exc:
        logger.exception("wordbank_db_operational_error")
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc}",
        ) from exc


@router.get("/wordbank/search/cor-lemma/{lemma_idx}", response_model=CORLemmaParadigmResponse)
def search_cor_lemma_paradigm(
    lemma_idx: int,
    request: Request,
    limit: int = Query(1000, ge=1, le=5000),
) -> CORLemmaParadigmResponse:
    _require_db_ready(request)

    try:
        return build_wordbank_use_case(request).search_cor_lemma_paradigm(lemma_idx, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
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
        return build_wordbank_use_case(request).get_lemma_details(lemma)
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


@router.get("/wordbank/pronunciation")
def get_pronunciation_audio(request: Request, form: str = Query(..., min_length=1)) -> Response:
    _require_db_ready(request)

    try:
        pronunciation = build_wordbank_use_case(request).get_pronunciation_audio(form)
        return Response(content=pronunciation.audio_bytes, media_type=pronunciation.mime_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
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
        response = build_wordbank_use_case(request).reset_database()
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
