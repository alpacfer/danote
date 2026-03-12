from fastapi import APIRouter, Request

from app.api.routes._runtime import get_runtime_state
from app.api.schemas.v1 import HealthResponse
from app.services.use_cases.health_status import build_health_status

router = APIRouter()


@router.get("/")
def api_root() -> dict[str, str]:
    return {"status": "ok", "message": "danote backend scaffold"}


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    runtime = get_runtime_state(request)
    return build_health_status(runtime)
