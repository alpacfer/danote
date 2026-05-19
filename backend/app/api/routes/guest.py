from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from app.api.routes._use_case_factories import build_trial_use_case
from app.api.schemas.v1 import GuestSessionRequest, GuestSessionResponse
from app.core.app_state import get_runtime_state

router = APIRouter(prefix="/guest", tags=["guest"])


@router.post("/sessions", response_model=GuestSessionResponse)
def create_guest_session(payload: GuestSessionRequest, request: Request) -> GuestSessionResponse:
    repo = get_runtime_state(request).guest_session_repository
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="guest_sessions_not_initialized",
        )
    try:
        session = repo.create(browser_id=payload.browser_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None
    trial = build_trial_use_case(request).guest_status(session.browser_id_hash)
    return GuestSessionResponse(token=session.token, auth_provider="guest", trial=trial)
