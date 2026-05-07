from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, Request, Response

from app.api.routes._runtime import get_services, get_settings, run_db_operation
from app.api.routes._use_case_factories import build_wordbank_use_case
from app.api.schemas.v1.wordbank import (
    AddWordRequest,
    AddWordResponse,
    ApplyVerificationChangesRequest,
    ApplyVerificationChangesResponse,
    CompleteVariationsRequest,
    CompleteVariationsResponse,
    CORLemmaParadigmResponse,
    CORSearchFormResponse,
    DetectWordLanguageRequest,
    DetectWordLanguageResponse,
    ENSearchFormResponse,
    FindAlternativeTranslationsRequest,
    FindAlternativeTranslationsResponse,
    GeneratePhraseTranslationRequest,
    GeneratePhraseTranslationResponse,
    GeneratePronunciationRequest,
    GeneratePronunciationResponse,
    GenerateReverseTranslationRequest,
    GenerateReverseTranslationResponse,
    GenerateTranslationRequest,
    GenerateTranslationResponse,
    GetVerificationChangesResponse,
    LemmaDetailsResponse,
    LemmaListResponse,
    QueueVerificationRequest,
    QueueVerificationResponse,
    ResetDatabaseResponse,
    SeedNumbersAudioResponse,
    SeedPresavedWordsAudioResponse,
    ResolveQueryRequest,
    ResolveQueryResponse,
    RethinkCategoriesRequest,
    RethinkCategoriesResponse,
    RevertVerificationChangeRequest,
    RevertVerificationChangeResponse,
    VerifyWordRequest,
    VerifyWordResponse,
    WordbankSearchResponse,
)
from app.core.app_state import set_runtime_field
from app.services.use_cases.numbers_pronunciation import (
    get_numbers_pronunciation_audio as _get_numbers_audio,
    seed_numbers_audio as _seed_numbers_audio,
)
from app.services.use_cases.presaved_words_pronunciation import (
    get_presaved_words_pronunciation_audio as _get_presaved_words_audio,
    seed_presaved_words_audio as _seed_presaved_words_audio,
)
from app.services.use_cases.wordbank.mappers import map_lemma_details_response

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/wordbank/lexemes", response_model=AddWordResponse)
def add_word(payload: AddWordRequest, request: Request) -> AddWordResponse:
    return run_db_operation(
        request,
        lambda: build_wordbank_use_case(request).add_word(
            payload.surface_token,
            payload.lemma_candidate,
            cor_id=payload.cor_id,
            pos_tag=payload.pos_tag,
            morphology=payload.morphology,
            search_seed=payload.search_seed.model_dump() if payload.search_seed is not None else None,
        ),
        include_runtime_error=True,
        error_log_name="wordbank_db_operational_error",
    )


@router.post("/wordbank/lexemes/verify", response_model=VerifyWordResponse)
def verify_added_word(payload: VerifyWordRequest, request: Request) -> VerifyWordResponse:
    return run_db_operation(
        request,
        lambda: build_wordbank_use_case(request).verify_added_word(
            payload.stored_lemma,
            payload.stored_surface_form,
            meaning_id=payload.meaning_id,
        ),
        error_log_name="wordbank_db_operational_error",
    )


@router.post("/wordbank/lexemes/queue-verification", response_model=QueueVerificationResponse)
def queue_verification(payload: QueueVerificationRequest, request: Request) -> QueueVerificationResponse:
    return run_db_operation(
        request,
        lambda: build_wordbank_use_case(request).queue_verification(
            payload.stored_lemma,
            payload.stored_surface_form,
            meaning_id=payload.meaning_id,
            review_intent=payload.review_intent or "general",
        ),
        include_lookup_error=True,
        error_log_name="wordbank_db_operational_error",
    )


@router.post("/wordbank/lexemes/rethink-categories", response_model=RethinkCategoriesResponse)
def rethink_categories(payload: RethinkCategoriesRequest, request: Request) -> RethinkCategoriesResponse:
    return run_db_operation(
        request,
        lambda: build_wordbank_use_case(request).rethink_categories(
            payload.stored_lemma,
            payload.stored_surface_form,
            meaning_id=payload.meaning_id,
        ),
        include_lookup_error=True,
        error_log_name="wordbank_db_operational_error",
    )


@router.post("/wordbank/lexemes/find-alternative-translations", response_model=FindAlternativeTranslationsResponse)
def find_alternative_translations(
    payload: FindAlternativeTranslationsRequest,
    request: Request,
) -> FindAlternativeTranslationsResponse:
    return run_db_operation(
        request,
        lambda: build_wordbank_use_case(request).find_alternative_translations(
            payload.stored_lemma,
            meaning_id=payload.meaning_id,
        ),
        include_lookup_error=True,
        error_log_name="wordbank_db_operational_error",
    )


@router.post("/wordbank/lexemes/complete-variations", response_model=CompleteVariationsResponse)
def complete_variations(
    payload: CompleteVariationsRequest,
    request: Request,
) -> CompleteVariationsResponse:
    return run_db_operation(
        request,
        lambda: build_wordbank_use_case(request).complete_meaning_variations(
            payload.stored_lemma,
            meaning_id=payload.meaning_id,
        ),
        include_lookup_error=True,
        error_log_name="wordbank_db_operational_error",
    )


@router.post("/wordbank/lexemes/pronunciation", response_model=GeneratePronunciationResponse)
def generate_pronunciation(payload: GeneratePronunciationRequest, request: Request) -> GeneratePronunciationResponse:
    return run_db_operation(
        request,
        lambda: build_wordbank_use_case(request).generate_pronunciation_for_added_word(
            payload.stored_lemma,
            payload.stored_surface_form,
            force=payload.force,
        ),
        include_lookup_error=True,
        error_log_name="wordbank_db_operational_error",
    )


@router.post("/wordbank/lexemes/apply-verification-changes", response_model=ApplyVerificationChangesResponse)
def apply_verification_changes(payload: ApplyVerificationChangesRequest, request: Request) -> ApplyVerificationChangesResponse:
    return run_db_operation(
        request,
        lambda: build_wordbank_use_case(request).apply_verification_changes(
            stored_lemma=payload.stored_lemma,
            stored_surface_form=payload.stored_surface_form,
            meaning_id=payload.meaning_id,
            action=payload.action.model_dump(),
            provider=payload.provider,
        ),
        include_lookup_error=True,
        error_log_name="wordbank_db_operational_error",
    )


@router.get("/wordbank/lexemes/verification-changes", response_model=GetVerificationChangesResponse)
def get_verification_changes(request: Request, stored_lemma: str = Query(..., min_length=1)) -> GetVerificationChangesResponse:
    return run_db_operation(
        request,
        lambda: build_wordbank_use_case(request).get_verification_changes(stored_lemma),
        error_log_name="wordbank_db_operational_error",
    )


@router.post("/wordbank/lexemes/revert-verification-change", response_model=RevertVerificationChangeResponse)
def revert_verification_change(payload: RevertVerificationChangeRequest, request: Request) -> RevertVerificationChangeResponse:
    return run_db_operation(
        request,
        lambda: build_wordbank_use_case(request).revert_verification_change(
            payload.change_id,
            payload.stored_lemma,
        ),
        error_log_name="wordbank_db_operational_error",
    )


@router.post("/wordbank/translation", response_model=GenerateTranslationResponse)
def generate_translation(payload: GenerateTranslationRequest, request: Request) -> GenerateTranslationResponse:
    return run_db_operation(
        request,
        lambda: build_wordbank_use_case(request).generate_translation(payload.surface_token, payload.lemma_candidate),
        error_log_name="wordbank_db_operational_error",
    )


@router.post("/wordbank/reverse-translation", response_model=GenerateReverseTranslationResponse)
def generate_reverse_translation(
    payload: GenerateReverseTranslationRequest,
    request: Request,
) -> GenerateReverseTranslationResponse:
    return run_db_operation(
        request,
        lambda: build_wordbank_use_case(request).generate_reverse_translation(payload.source_word),
        error_log_name="wordbank_db_operational_error",
    )


@router.post("/wordbank/detect-language", response_model=DetectWordLanguageResponse)
def detect_word_language(
    payload: DetectWordLanguageRequest,
    request: Request,
) -> DetectWordLanguageResponse:
    return run_db_operation(
        request,
        lambda: build_wordbank_use_case(request).detect_word_language(payload.source_word),
        error_log_name="wordbank_db_operational_error",
    )


@router.post("/wordbank/resolve-query", response_model=ResolveQueryResponse)
def resolve_query(payload: ResolveQueryRequest, request: Request) -> ResolveQueryResponse:
    return run_db_operation(
        request,
        lambda: build_wordbank_use_case(request).resolve_query(
            payload.query_text,
            include_translations=payload.include_translations,
            include_language_detection=payload.include_language_detection,
        ),
        error_log_name="wordbank_db_operational_error",
    )


@router.post("/wordbank/phrase-translation", response_model=GeneratePhraseTranslationResponse)
def generate_phrase_translation(
    payload: GeneratePhraseTranslationRequest,
    request: Request,
) -> GeneratePhraseTranslationResponse:
    return run_db_operation(
        request,
        lambda: build_wordbank_use_case(request).generate_phrase_translation(payload.source_text),
        error_log_name="wordbank_db_operational_error",
    )


@router.get("/wordbank/lemmas", response_model=LemmaListResponse)
def list_lemmas(request: Request) -> LemmaListResponse:
    return run_db_operation(
        request,
        lambda: build_wordbank_use_case(request).list_lemmas(),
        include_runtime_error=True,
        error_log_name="wordbank_db_operational_error",
    )


@router.get("/wordbank/search", response_model=WordbankSearchResponse)
def search_wordbank(
    request: Request,
    query: str = Query(..., min_length=1),
    limit: int = Query(8, ge=1, le=50),
) -> WordbankSearchResponse:
    return run_db_operation(
        request,
        lambda: build_wordbank_use_case(request).search_lemmas(query, limit=limit),
        include_runtime_error=True,
        error_log_name="wordbank_db_operational_error",
    )


@router.get("/wordbank/search/cor-form", response_model=CORSearchFormResponse)
def search_cor_form(
    request: Request,
    form: str = Query(..., min_length=1),
    limit: int = Query(100, ge=1, le=500),
    include_translations: bool = Query(True),
) -> CORSearchFormResponse:
    return run_db_operation(
        request,
        lambda: build_wordbank_use_case(request).search_cor_form(form, limit=limit, include_translations=include_translations),
        include_runtime_error=True,
        error_log_name="wordbank_db_operational_error",
    )


@router.get("/wordbank/search/en-form", response_model=ENSearchFormResponse)
def search_en_form(
    request: Request,
    form: str = Query(..., min_length=1),
    include_translations: bool = Query(True),
) -> ENSearchFormResponse:
    return run_db_operation(
        request,
        lambda: build_wordbank_use_case(request).search_en_form(
            form,
            include_translations=include_translations,
        ),
        include_runtime_error=True,
        error_log_name="wordbank_db_operational_error",
    )


@router.get("/wordbank/search/cor-lemma/{lemma_idx}", response_model=CORLemmaParadigmResponse)
def search_cor_lemma_paradigm(
    lemma_idx: int,
    request: Request,
    limit: int = Query(1000, ge=1, le=5000),
) -> CORLemmaParadigmResponse:
    return run_db_operation(
        request,
        lambda: build_wordbank_use_case(request).search_cor_lemma_paradigm(lemma_idx, limit=limit),
        include_runtime_error=True,
        error_log_name="wordbank_db_operational_error",
    )


@router.get("/wordbank/lemmas/{lemma}", response_model=LemmaDetailsResponse)
def get_lemma_details(lemma: str, request: Request) -> LemmaDetailsResponse:
    response = run_db_operation(
        request,
        lambda: build_wordbank_use_case(request).get_lemma_details(lemma),
        include_lookup_error=True,
        include_runtime_error=True,
        error_log_name="wordbank_db_operational_error",
    )
    return map_lemma_details_response(response)


@router.get("/wordbank/pronunciation")
def get_pronunciation_audio(request: Request, form: str = Query(..., min_length=1)) -> Response:
    pronunciation = run_db_operation(
        request,
        lambda: build_wordbank_use_case(request).get_pronunciation_audio(form),
        include_lookup_error=True,
        include_runtime_error=True,
        error_log_name="wordbank_db_operational_error",
    )
    return Response(content=pronunciation.audio_bytes, media_type=pronunciation.mime_type)


@router.get("/wordbank/numbers/pronunciation")
def get_numbers_pronunciation_audio(request: Request, term: str = Query(..., min_length=1)) -> Response:
    pronunciation = run_db_operation(
        request,
        lambda: _get_numbers_audio(term, get_settings(request).db_path),
        include_lookup_error=True,
        error_log_name="numbers_pronunciation_db_operational_error",
    )
    return Response(content=pronunciation.audio_bytes, media_type=pronunciation.mime_type)


@router.post("/wordbank/numbers/pronunciation/seed", response_model=SeedNumbersAudioResponse)
def seed_numbers_pronunciation_audio(request: Request) -> SeedNumbersAudioResponse:
    tts_service = get_services(request).tts_service
    db_path = get_settings(request).db_path
    result = run_db_operation(
        request,
        lambda: _seed_numbers_audio(tts_service, db_path),
        include_runtime_error=True,
        error_log_name="numbers_seed_db_operational_error",
    )
    parts = []
    if result.generated:
        parts.append(f"{result.generated} generated")
    if result.skipped:
        parts.append(f"{result.skipped} already stored")
    if result.failed:
        parts.append(f"{result.failed} failed")
    message = ", ".join(parts) if parts else "Nothing to do."
    return SeedNumbersAudioResponse(
        generated=result.generated,
        skipped=result.skipped,
        failed=result.failed,
        message=message,
    )


@router.get("/wordbank/presaved-words/pronunciation")
def get_presaved_words_pronunciation_audio(request: Request, term: str = Query(..., min_length=1)) -> Response:
    pronunciation = run_db_operation(
        request,
        lambda: _get_presaved_words_audio(term, get_settings(request).db_path),
        include_lookup_error=True,
        error_log_name="presaved_words_pronunciation_db_operational_error",
    )
    return Response(content=pronunciation.audio_bytes, media_type=pronunciation.mime_type)


@router.post("/wordbank/presaved-words/pronunciation/seed", response_model=SeedPresavedWordsAudioResponse)
def seed_presaved_words_pronunciation_audio(
    request: Request,
    force: bool = Query(False),
) -> SeedPresavedWordsAudioResponse:
    tts_service = get_services(request).tts_service
    db_path = get_settings(request).db_path
    result = run_db_operation(
        request,
        lambda: _seed_presaved_words_audio(tts_service, db_path, force=force),
        include_runtime_error=True,
        error_log_name="presaved_words_seed_db_operational_error",
    )
    parts = []
    if result.generated:
        parts.append(f"{result.generated} generated")
    if result.skipped:
        parts.append(f"{result.skipped} already stored")
    if result.failed:
        parts.append(f"{result.failed} failed")
    message = ", ".join(parts) if parts else "Nothing to do."
    return SeedPresavedWordsAudioResponse(
        generated=result.generated,
        skipped=result.skipped,
        failed=result.failed,
        message=message,
    )


@router.delete("/wordbank/database", response_model=ResetDatabaseResponse)
def reset_database(request: Request) -> ResetDatabaseResponse:
    try:
        response = run_db_operation(
            request,
            lambda: build_wordbank_use_case(request).reset_database(),
            error_log_name="wordbank_db_reset_operational_error",
        )
        set_runtime_field(request.app, "db_ready", True)
        set_runtime_field(request.app, "db_error", None)
        return response
    except OSError as exc:
        logger.exception("wordbank_db_reset_os_error")
        raise HTTPException(status_code=503, detail=f"Database reset failed: {exc}") from exc
