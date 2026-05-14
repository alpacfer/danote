from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any

import httpx
import jwt
from fastapi import HTTPException, Request, status

from app.core.app_state import get_runtime_state, get_settings
from app.db.repositories.users import AppUserRecord, AppUserRepository

logger = logging.getLogger(__name__)

# Local-dev fallback user id. Matches the legacy row seeded by migration 027.
_LEGACY_USER_ID = 1
_JWKS_CACHE_SECONDS = 600


@dataclass(frozen=True)
class CurrentUser:
    id: int
    email: str | None
    auth_provider: str
    auth_subject: str
    display_name: str | None
    created_at: str
    last_seen_at: str


class _JWKSClient:
    """Thread-safe JWKS fetcher with TTL caching and forced-refresh on miss."""

    def __init__(self, jwks_url: str) -> None:
        self._jwks_url = jwks_url
        self._lock = threading.Lock()
        self._cached: dict[str, Any] | None = None
        self._fetched_at: float = 0.0

    def _fetch(self) -> dict[str, Any]:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(self._jwks_url)
            response.raise_for_status()
            return response.json()

    def get_keys(self, *, force_refresh: bool = False) -> dict[str, Any]:
        with self._lock:
            now = time.time()
            stale = self._cached is None or (now - self._fetched_at) > _JWKS_CACHE_SECONDS
            if force_refresh or stale:
                self._cached = self._fetch()
                self._fetched_at = now
            return self._cached  # type: ignore[return-value]


def build_jwks_client(jwks_url: str | None) -> _JWKSClient | None:
    if not jwks_url:
        return None
    return _JWKSClient(jwks_url)


def _is_email_allowed(email: str | None, allowed: tuple[str, ...], allowed_domains: tuple[str, ...]) -> bool:
    if not allowed and not allowed_domains:
        return True
    if email is None:
        return False
    lower = email.strip().lower()
    if lower in allowed:
        return True
    for domain in allowed_domains:
        if lower.endswith(f"@{domain}"):
            return True
    return False


def _select_signing_key(jwks: dict[str, Any], kid: str | None) -> dict[str, Any] | None:
    keys = jwks.get("keys") or []
    if not isinstance(keys, list):
        return None
    if kid is None:
        return keys[0] if keys else None
    for entry in keys:
        if isinstance(entry, dict) and entry.get("kid") == kid:
            return entry
    return None


def _verify_clerk_token(
    token: str,
    *,
    jwks_client: _JWKSClient,
    issuer: str | None,
    audience: str | None,
) -> dict[str, Any]:
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")
    algorithm = unverified_header.get("alg", "RS256")

    def _decode(jwks_payload: dict[str, Any]) -> dict[str, Any]:
        key = _select_signing_key(jwks_payload, kid)
        if key is None:
            raise jwt.PyJWTError("no matching JWK")
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)  # type: ignore[attr-defined]
        options = {"require": ["exp", "iat"]}
        decode_kwargs: dict[str, Any] = {
            "algorithms": [algorithm],
            "options": options,
        }
        if audience:
            decode_kwargs["audience"] = audience
        if issuer:
            decode_kwargs["issuer"] = issuer
        return jwt.decode(token, public_key, **decode_kwargs)

    try:
        return _decode(jwks_client.get_keys())
    except jwt.PyJWTError:
        # Force-refresh and try once more in case Clerk rotated keys.
        return _decode(jwks_client.get_keys(force_refresh=True))


def _claims_to_user(claims: dict[str, Any]) -> tuple[str, str, str | None, str | None]:
    subject = str(claims.get("sub") or "")
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token")
    email_raw = claims.get("email") or claims.get("primary_email_address") or claims.get("user_email")
    name_raw = claims.get("name") or claims.get("full_name")
    email = str(email_raw) if email_raw else None
    display_name = str(name_raw) if name_raw else None
    return "clerk", subject, email, display_name


def _extract_bearer(request: Request) -> str | None:
    header = request.headers.get("Authorization") or request.headers.get("authorization")
    if not header:
        return None
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token.strip()


_LOCAL_DEV_PROVIDER = "local"
_LOCAL_DEV_SUBJECT = "local-dev"
_LOCAL_DEV_EMAIL = "local@danote.local"
_LOCAL_DEV_DISPLAY_NAME = "Local Danote User"


def _local_dev_user(users_repo: AppUserRepository | None) -> CurrentUser:
    if users_repo is None:
        now = ""
        return CurrentUser(
            id=_LEGACY_USER_ID,
            email=_LOCAL_DEV_EMAIL,
            auth_provider=_LOCAL_DEV_PROVIDER,
            auth_subject=_LOCAL_DEV_SUBJECT,
            display_name=_LOCAL_DEV_DISPLAY_NAME,
            created_at=now,
            last_seen_at=now,
        )
    record = users_repo.upsert_user(
        auth_provider=_LOCAL_DEV_PROVIDER,
        auth_subject=_LOCAL_DEV_SUBJECT,
        email=_LOCAL_DEV_EMAIL,
        display_name=_LOCAL_DEV_DISPLAY_NAME,
    )
    return _record_to_current_user(record)


def _record_to_current_user(record: AppUserRecord) -> CurrentUser:
    return CurrentUser(
        id=record.id,
        email=record.email,
        auth_provider=record.auth_provider,
        auth_subject=record.auth_subject,
        display_name=record.display_name,
        created_at=record.created_at,
        last_seen_at=record.last_seen_at,
    )


def require_current_user(request: Request) -> CurrentUser:
    settings = get_settings(request)
    runtime = get_runtime_state(request)
    users_repo: AppUserRepository | None = runtime.users_repository

    if not settings.auth_enabled:
        return _local_dev_user(users_repo)

    if users_repo is None:
        logger.error("auth_users_repo_missing")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="auth_not_initialized",
        )

    token = _extract_bearer(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_bearer_token")

    jwks_client: _JWKSClient | None = runtime.clerk_jwks_client
    if jwks_client is None:
        logger.error("auth_jwks_client_missing")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="auth_not_initialized",
        )

    try:
        claims = _verify_clerk_token(
            token,
            jwks_client=jwks_client,
            issuer=settings.clerk_issuer,
            audience=settings.clerk_audience,
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token_expired") from None
    except jwt.PyJWTError as exc:
        logger.info("auth_token_rejected", extra={"error": str(exc)})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token") from None
    except httpx.HTTPError as exc:
        logger.error("auth_jwks_fetch_failed", extra={"error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="auth_jwks_unavailable",
        ) from None

    provider, subject, email, display_name = _claims_to_user(claims)

    if not _is_email_allowed(email, settings.allowed_emails, settings.allowed_email_domains):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="email_not_allowed")

    record = users_repo.upsert_user(
        auth_provider=provider,
        auth_subject=subject,
        email=email,
        display_name=display_name,
    )
    return _record_to_current_user(record)


def get_current_user_response(request: Request):
    """Return the schema-shaped CurrentUserResponse for the request's user.

    Imported lazily to avoid a circular import between the auth module and
    the schemas package at import time.
    """
    from app.api.schemas.v1 import CurrentUserResponse

    user = require_current_user(request)
    return CurrentUserResponse(
        id=user.id,
        auth_provider=user.auth_provider,
        auth_subject=user.auth_subject,
        email=user.email,
        display_name=user.display_name,
        created_at=user.created_at,
        last_seen_at=user.last_seen_at,
    )
