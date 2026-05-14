from __future__ import annotations

import logging

from fastapi import FastAPI

from app.api.auth import build_jwks_client
from app.core.app_state import set_runtime_field
from app.core.config import Settings
from app.db.repositories.user_api_keys import UserApiKeysRepository
from app.db.repositories.users import AppUserRepository
from app.services.key_encryption import KeyEncryptionConfigError, KeyEncryptionService

logger = logging.getLogger(__name__)


def initialize_auth(app: FastAPI, settings: Settings) -> None:
    """Wire up users repo, key encryption, key repo, and Clerk JWKS client.

    Failures are recorded on `runtime.auth_error` rather than raising so the
    rest of the app can still boot in degraded mode (e.g. for local dev where
    `DANOTE_AUTH_ENABLED=0`).
    """

    set_runtime_field(app, "auth_error", None)

    users_repo = AppUserRepository(settings.db_path)
    set_runtime_field(app, "users_repository", users_repo)

    encryption: KeyEncryptionService | None = None
    secret = settings.key_encryption_secret
    if secret:
        try:
            encryption = KeyEncryptionService.from_base64_secret(secret)
        except KeyEncryptionConfigError as exc:
            logger.error("auth_key_encryption_invalid", extra={"error": str(exc)})
            set_runtime_field(app, "auth_error", f"key_encryption_invalid:{exc}")

    if encryption is not None:
        set_runtime_field(app, "key_encryption", encryption)
        set_runtime_field(
            app,
            "user_api_keys_repository",
            UserApiKeysRepository(settings.db_path, encryption),
        )
    elif settings.auth_enabled:
        logger.warning(
            "auth_key_encryption_missing",
            extra={"hint": "set DANOTE_KEY_ENCRYPTION_SECRET (base64 32-byte key)"},
        )
        set_runtime_field(
            app,
            "auth_error",
            "key_encryption_secret_missing",
        )

    if settings.auth_enabled:
        jwks_client = build_jwks_client(settings.clerk_jwks_url)
        if jwks_client is None:
            logger.warning(
                "auth_clerk_jwks_url_missing",
                extra={"hint": "set DANOTE_CLERK_JWKS_URL"},
            )
            set_runtime_field(app, "auth_error", "clerk_jwks_url_missing")
        else:
            set_runtime_field(app, "clerk_jwks_client", jwks_client)
