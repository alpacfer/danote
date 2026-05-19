from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.auth import CurrentUser, require_current_user
from app.api.routes._use_case_factories import build_account_use_case
from app.api.schemas.v1 import (
    AccountMeResponse,
    AccountStatusResponse,
    TestApiKeyResponse,
    TrialOptInResponse,
    UpdateApiKeyRequest,
    UpdateApiKeyResponse,
)
from app.services.use_cases.account import (
    GuestApiKeysForbiddenError,
    KeyStorageUnavailableError,
    UnsupportedApiKeyProviderError,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/account", tags=["account"])
CURRENT_USER_DEP = Depends(require_current_user)


def _map_account_error(exc: Exception) -> HTTPException:
    if isinstance(exc, GuestApiKeysForbiddenError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="guest_api_keys_forbidden")
    if isinstance(exc, KeyStorageUnavailableError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="key_storage_not_initialized",
        )
    if isinstance(exc, UnsupportedApiKeyProviderError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unsupported_provider:{exc}",
        )
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/me", response_model=AccountMeResponse)
def get_me(current_user: CurrentUser = CURRENT_USER_DEP) -> AccountMeResponse:
    return AccountMeResponse(
        id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name,
        auth_provider=current_user.auth_provider,
    )


@router.get("/status", response_model=AccountStatusResponse)
def get_status(
    request: Request,
    current_user: CurrentUser = CURRENT_USER_DEP,
) -> AccountStatusResponse:
    try:
        return build_account_use_case(request).status(
            user_id=current_user.id,
            auth_provider=current_user.auth_provider,
            guest_browser_id_hash=current_user.guest_browser_id_hash,
        )
    except Exception as exc:
        raise _map_account_error(exc) from None


@router.post("/trial/opt-in", response_model=TrialOptInResponse)
def opt_in_trial(
    request: Request,
    current_user: CurrentUser = CURRENT_USER_DEP,
) -> TrialOptInResponse:
    try:
        return build_account_use_case(request).opt_in_trial(
            user_id=current_user.id,
            auth_provider=current_user.auth_provider,
            guest_browser_id_hash=current_user.guest_browser_id_hash,
        )
    except Exception as exc:
        raise _map_account_error(exc) from None


@router.put("/api-keys/{provider}", response_model=UpdateApiKeyResponse)
def upsert_api_key(
    provider: str,
    payload: UpdateApiKeyRequest,
    request: Request,
    current_user: CurrentUser = CURRENT_USER_DEP,
) -> UpdateApiKeyResponse:
    try:
        return build_account_use_case(request).upsert_api_key(
            user_id=current_user.id,
            auth_provider=current_user.auth_provider,
            provider=provider,
            value=payload.value,
        )
    except Exception as exc:
        raise _map_account_error(exc) from None


@router.delete("/api-keys/{provider}", response_model=UpdateApiKeyResponse)
def delete_api_key(
    provider: str,
    request: Request,
    current_user: CurrentUser = CURRENT_USER_DEP,
) -> UpdateApiKeyResponse:
    try:
        return build_account_use_case(request).delete_api_key(
            user_id=current_user.id,
            auth_provider=current_user.auth_provider,
            provider=provider,
        )
    except Exception as exc:
        raise _map_account_error(exc) from None


@router.post("/api-keys/{provider}/test", response_model=TestApiKeyResponse)
def test_api_key(
    provider: str,
    request: Request,
    current_user: CurrentUser = CURRENT_USER_DEP,
) -> TestApiKeyResponse:
    try:
        return build_account_use_case(request).test_api_key(
            user_id=current_user.id,
            auth_provider=current_user.auth_provider,
            provider=provider,
        )
    except Exception as exc:
        raise _map_account_error(exc) from None
