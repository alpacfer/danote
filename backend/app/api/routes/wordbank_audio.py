from __future__ import annotations

from fastapi import APIRouter, Query, Request, Response

from app.api.routes._runtime import get_services, get_settings, run_db_operation
from app.api.routes._use_case_factories import build_wordbank_use_case
from app.api.schemas.v1.wordbank import (
    SeedNumbersAudioResponse,
    SeedPresavedWordsAudioResponse,
)
from app.services.use_cases.numbers_pronunciation import (
    get_numbers_pronunciation_audio as _get_numbers_audio,
)
from app.services.use_cases.numbers_pronunciation import (
    seed_numbers_audio as _seed_numbers_audio,
)
from app.services.use_cases.presaved_words_pronunciation import (
    get_presaved_words_pronunciation_audio as _get_presaved_words_audio,
)
from app.services.use_cases.presaved_words_pronunciation import (
    seed_presaved_words_audio as _seed_presaved_words_audio,
)

router = APIRouter()


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
def seed_numbers_pronunciation_audio(
    request: Request,
    force: bool = Query(False),
) -> SeedNumbersAudioResponse:
    tts_service = get_services(request).tts_service
    db_path = get_settings(request).db_path
    result = run_db_operation(
        request,
        lambda: _seed_numbers_audio(tts_service, db_path, force=force),
        include_runtime_error=True,
        error_log_name="numbers_seed_db_operational_error",
    )
    return SeedNumbersAudioResponse(
        generated=result.generated,
        skipped=result.skipped,
        failed=result.failed,
        message=_seed_message(result.generated, result.skipped, result.failed),
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
    return SeedPresavedWordsAudioResponse(
        generated=result.generated,
        skipped=result.skipped,
        failed=result.failed,
        message=_seed_message(result.generated, result.skipped, result.failed),
    )


def _seed_message(generated: int, skipped: int, failed: int) -> str:
    parts = []
    if generated:
        parts.append(f"{generated} generated")
    if skipped:
        parts.append(f"{skipped} already stored")
    if failed:
        parts.append(f"{failed} failed")
    return ", ".join(parts) if parts else "Nothing to do."
