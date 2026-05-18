from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.auth import CurrentUser, require_current_user
from app.api.routes._use_case_factories import build_trial_use_case
from app.api.schemas.v1 import (
    AccountMeResponse,
    AccountStatusResponse,
    ApiKeyStatus,
    TestApiKeyResponse,
    TrialOptInResponse,
    UpdateApiKeyRequest,
    UpdateApiKeyResponse,
)
from app.core.app_state import get_runtime_state
from app.db.repositories.user_api_keys import (
    SUPPORTED_PROVIDERS,
    UnknownProviderError,
    UserApiKeysRepository,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/account", tags=["account"])


def _resolve_keys_repo(request: Request) -> UserApiKeysRepository:
    runtime = get_runtime_state(request)
    repo: UserApiKeysRepository | None = runtime.user_api_keys_repository
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="key_storage_not_initialized",
        )
    return repo


@router.get("/me", response_model=AccountMeResponse)
def get_me(current_user: CurrentUser = Depends(require_current_user)) -> AccountMeResponse:
    return AccountMeResponse(
        id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name,
        auth_provider=current_user.auth_provider,
    )


@router.get("/status", response_model=AccountStatusResponse)
def get_status(
    request: Request,
    current_user: CurrentUser = Depends(require_current_user),
) -> AccountStatusResponse:
    repo = _resolve_keys_repo(request)
    snapshot = repo.status(user_id=current_user.id)
    providers = {
        name: ApiKeyStatus(provider=name, is_set=meta.is_set, last_four=meta.last_four)
        for name, meta in snapshot.items()
    }
    missing = [name for name, meta in snapshot.items() if not meta.is_set]
    trial = build_trial_use_case(request).status(current_user.id)
    return AccountStatusResponse(
        keys_configured=not missing,
        providers=providers,
        missing=missing,
        trial=trial,
    )


@router.post("/trial/opt-in", response_model=TrialOptInResponse)
def opt_in_trial(
    request: Request,
    current_user: CurrentUser = Depends(require_current_user),
) -> TrialOptInResponse:
    trial = build_trial_use_case(request).opt_in(current_user.id)
    return TrialOptInResponse(trial=trial)


def _ensure_supported(provider: str) -> None:
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unsupported_provider:{provider}",
        )


@router.put("/api-keys/{provider}", response_model=UpdateApiKeyResponse)
def upsert_api_key(
    provider: str,
    payload: UpdateApiKeyRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_current_user),
) -> UpdateApiKeyResponse:
    _ensure_supported(provider)
    repo = _resolve_keys_repo(request)
    try:
        meta = repo.upsert(user_id=current_user.id, provider=provider, plaintext=payload.value)
    except UnknownProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unsupported_provider:{exc}",
        ) from None
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None
    return UpdateApiKeyResponse(provider=meta.provider, is_set=meta.is_set, last_four=meta.last_four)


@router.delete("/api-keys/{provider}", response_model=UpdateApiKeyResponse)
def delete_api_key(
    provider: str,
    request: Request,
    current_user: CurrentUser = Depends(require_current_user),
) -> UpdateApiKeyResponse:
    _ensure_supported(provider)
    repo = _resolve_keys_repo(request)
    repo.delete(user_id=current_user.id, provider=provider)
    return UpdateApiKeyResponse(provider=provider, is_set=False, last_four=None)


@router.post("/api-keys/{provider}/test", response_model=TestApiKeyResponse)
def test_api_key(
    provider: str,
    request: Request,
    current_user: CurrentUser = Depends(require_current_user),
) -> TestApiKeyResponse:
    _ensure_supported(provider)
    repo = _resolve_keys_repo(request)
    plaintext = repo.get_plaintext(user_id=current_user.id, provider=provider)
    if plaintext is None:
        return TestApiKeyResponse(provider=provider, ok=False, error="key_not_set")
    # Cheap structural probe only — the per-request key resolution layer
    # exercises the real APIs at call time. Avoids surprise outbound calls here.
    ok = len(plaintext.strip()) >= 8
    return TestApiKeyResponse(
        provider=provider,
        ok=ok,
        error=None if ok else "key_too_short",
    )
