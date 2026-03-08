from fastapi import APIRouter, Request

from app.api.schemas.v1 import (
    DeveloperApiKeysUpdateRequest,
    DeveloperApiKeysUpdateResponse,
    DeveloperServiceProbeResponse,
    GeminiProbeResponse,
)
from app.services.use_cases.developer import DeveloperUseCase

router = APIRouter()


@router.post("/developer/api-keys", response_model=DeveloperApiKeysUpdateResponse)
def update_api_keys(payload: DeveloperApiKeysUpdateRequest, request: Request) -> DeveloperApiKeysUpdateResponse:
    return DeveloperUseCase(request.app).update_api_keys(payload)


@router.post("/developer/gemini-probe", response_model=GeminiProbeResponse)
def run_gemini_probe(request: Request) -> GeminiProbeResponse:
    return DeveloperUseCase(request.app).run_gemini_probe()


@router.post("/developer/translation-probe", response_model=DeveloperServiceProbeResponse)
def run_translation_probe(request: Request) -> DeveloperServiceProbeResponse:
    return DeveloperUseCase(request.app).run_translation_probe()


@router.post("/developer/tts-probe", response_model=DeveloperServiceProbeResponse)
def run_tts_probe(request: Request) -> DeveloperServiceProbeResponse:
    return DeveloperUseCase(request.app).run_tts_probe()
