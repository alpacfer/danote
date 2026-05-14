from __future__ import annotations

import logging

from fastapi import FastAPI

from app.core.app_state import get_runtime_state, set_runtime_field
from app.core.config import Settings
from app.services.user_service_resolver import UserServiceResolver

logger = logging.getLogger(__name__)


def initialize_user_service_resolver(app: FastAPI, settings: Settings) -> None:
    """Build the per-request user-service resolver.

    Must run AFTER all host-level services and the user-keys repository are wired,
    since the resolver captures references to both.
    """
    runtime = get_runtime_state(app)
    resolver = UserServiceResolver(
        settings=settings,
        user_api_keys_repository=runtime.user_api_keys_repository,
        fallback_services=runtime.services,
    )
    set_runtime_field(app, "user_service_resolver", resolver)
    logger.info(
        "user_service_resolver_initialized",
        extra={"user_keys_repo_present": runtime.user_api_keys_repository is not None},
    )
