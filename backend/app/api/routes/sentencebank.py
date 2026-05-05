from __future__ import annotations

import logging

from fastapi import APIRouter, Query, Request, Response

from app.api.routes._runtime import (
    get_services,
    get_settings,
    run_db_operation,
)
from app.api.routes._use_case_factories import build_wordbank_use_case
from app.api.schemas.v1.sentencebank import (
    AddSentenceRequest,
    AddSentenceResponse,
    GenerateExamplePreviewRequest,
    GenerateExamplePreviewResponse,
    GenerateSentencePronunciationRequest,
    GenerateSentencePronunciationResponse,
    GenerateStaticExamplePreviewRequest,
    SaveSentenceTokenResponse,
    SentenceListResponse,
    SentenceSearchPreviewRequest,
    SentenceSearchPreviewResponse,
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
        tts_service=services.tts_service,
    )


@router.post("/sentencebank/sentences", response_model=AddSentenceResponse)
def add_sentence(payload: AddSentenceRequest, request: Request) -> AddSentenceResponse:
    return run_db_operation(
        request,
        lambda: _sentencebank_use_case(request).add_sentence(
            payload.source_text,
            english_translation=payload.english_translation,
            token_persistence_mode=payload.token_persistence_mode,
            target=payload.target,
        ),
        error_log_name="sentencebank_db_operational_error",
    )


@router.post("/sentencebank/example-preview", response_model=GenerateExamplePreviewResponse)
def generate_example_preview(
    payload: GenerateExamplePreviewRequest,
    request: Request,
) -> GenerateExamplePreviewResponse:
    return run_db_operation(
        request,
        lambda: _sentencebank_use_case(request).generate_example_preview(
            payload.stored_lemma,
            payload.meaning_id,
            tense_label=payload.tense_label,
        ),
        include_lookup_error=True,
        include_runtime_error=True,
        error_log_name="sentencebank_example_preview_db_operational_error",
    )


@router.post("/sentencebank/static-example-preview", response_model=GenerateExamplePreviewResponse)
def generate_static_example_preview(
    payload: GenerateStaticExamplePreviewRequest,
    request: Request,
) -> GenerateExamplePreviewResponse:
    return run_db_operation(
        request,
        lambda: _sentencebank_use_case(request).generate_static_example_preview(payload.stored_lemma),
        include_lookup_error=True,
        include_runtime_error=True,
        error_log_name="sentencebank_static_example_preview_db_operational_error",
    )


@router.get("/sentencebank/sentences", response_model=SentenceListResponse)
def list_sentences(request: Request) -> SentenceListResponse:
    return run_db_operation(
        request,
        lambda: _sentencebank_use_case(request).list_sentences(),
        error_log_name="sentencebank_db_operational_error",
    )


@router.post(
    "/sentencebank/sentences/{sentence_id}/tokens/{token_index}/save",
    response_model=SaveSentenceTokenResponse,
)
def save_sentence_token(
    sentence_id: int,
    token_index: int,
    request: Request,
) -> SaveSentenceTokenResponse:
    return run_db_operation(
        request,
        lambda: _sentencebank_use_case(request).save_sentence_token(sentence_id, token_index),
        include_lookup_error=True,
        include_runtime_error=True,
        error_log_name="sentencebank_save_token_db_operational_error",
    )


@router.post("/sentencebank/verify-sentence", response_model=VerifySentenceResponse)
def verify_sentence(payload: VerifySentenceRequest, request: Request) -> VerifySentenceResponse:
    return run_db_operation(
        request,
        lambda: _sentencebank_use_case(request).verify_sentence(payload.source_text),
        error_log_name="sentencebank_verify_db_operational_error",
    )


@router.post("/sentencebank/search-preview", response_model=SentenceSearchPreviewResponse)
def sentence_search_preview(
    payload: SentenceSearchPreviewRequest,
    request: Request,
) -> SentenceSearchPreviewResponse:
    return run_db_operation(
        request,
        lambda: _sentencebank_use_case(request).preview_sentence_search(
            payload.source_text,
            fast=payload.fast,
        ),
        error_log_name="sentencebank_search_preview_db_operational_error",
    )


@router.post(
    "/sentencebank/sentences/pronunciation",
    response_model=GenerateSentencePronunciationResponse,
)
def generate_sentence_pronunciation(
    payload: GenerateSentencePronunciationRequest,
    request: Request,
) -> GenerateSentencePronunciationResponse:
    return run_db_operation(
        request,
        lambda: _sentencebank_use_case(request).generate_pronunciation_for_sentence(
            payload.sentence_id,
            force=payload.force,
        ),
        include_lookup_error=True,
        error_log_name="sentencebank_db_operational_error",
    )


@router.get("/sentencebank/pronunciation")
def get_sentence_pronunciation_audio(
    request: Request,
    sentence_id: int = Query(..., ge=1),
) -> Response:
    pronunciation = run_db_operation(
        request,
        lambda: _sentencebank_use_case(request).get_pronunciation_audio(sentence_id),
        include_lookup_error=True,
        include_runtime_error=True,
        error_log_name="sentencebank_db_operational_error",
    )
    return Response(content=pronunciation.audio_bytes, media_type=pronunciation.mime_type)
