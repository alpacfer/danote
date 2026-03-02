from fastapi import APIRouter, Request

from app.api.schemas.v1 import DeveloperApiKeysUpdateRequest, DeveloperApiKeysUpdateResponse
from app.services.use_cases.developer import DeveloperUseCase

router = APIRouter()


@router.post("/developer/api-keys", response_model=DeveloperApiKeysUpdateResponse)
def update_api_keys(payload: DeveloperApiKeysUpdateRequest, request: Request) -> DeveloperApiKeysUpdateResponse:
    return DeveloperUseCase(request.app).update_api_keys(payload)
