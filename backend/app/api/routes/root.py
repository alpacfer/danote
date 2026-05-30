import logging

from fastapi import APIRouter, Request

from app.api.auth import get_current_user_response
from app.api.routes._runtime import get_runtime_state
from app.api.schemas.v1 import CurrentUserResponse, HealthResponse
from app.services.use_cases.health_status import build_health_status

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
def api_root() -> dict[str, str]:
    return {"status": "ok", "message": "danote backend scaffold"}


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    runtime = get_runtime_state(request)
    response = build_health_status(runtime)
    logger.info(
        "health_check_memory_usage",
        extra={
            "memory_usage_kb": response.memory_usage_kb,
            "memory_usage_mb": round((response.memory_usage_kb or 0) / 1024, 2) if response.memory_usage_kb else 0.0,
        }
    )
    return response


@router.get("/me", response_model=CurrentUserResponse)
def me(request: Request) -> CurrentUserResponse:
    return get_current_user_response(request)
