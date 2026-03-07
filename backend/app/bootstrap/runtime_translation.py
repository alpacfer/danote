from __future__ import annotations

import logging

from fastapi import FastAPI

from app.core.app_state import get_runtime_state, set_runtime_field, set_service_field
from app.core.config import Settings
from app.services.translation import AzureTranslationService

logger = logging.getLogger(__name__)


RuntimeApiKeyOverrides = dict[str, str | None]


def initialize_translation(
    app: FastAPI,
    settings: Settings,
    overrides: RuntimeApiKeyOverrides | None = None,
) -> None:
    set_runtime_field(app, "translation_error", None)
    _close_service(get_runtime_state(app).services.translation_service)
    set_service_field(app, "translation_service", None)
    if not settings.translation_enabled:
        return

    provider = settings.translation_provider.strip().lower()
    if provider != "azure":
        logger.warning(
            "backend_translation_startup_skipped_unknown_provider",
            extra={"translation_provider": provider},
        )
        set_runtime_field(app, "translation_error", f"Unknown translation provider '{provider}'.")
        return

    azure_key = _override_or_setting(overrides, "translation_azure_api_key", settings.translation_azure_api_key)
    azure_region = _override_or_setting(overrides, "translation_azure_region", settings.translation_azure_region)
    azure_endpoint = _override_or_setting(overrides, "translation_azure_endpoint", settings.translation_azure_endpoint)

    if azure_key and azure_region:
        try:
            set_service_field(
                app,
                "translation_service",
                AzureTranslationService(
                    api_key=azure_key,
                    region=azure_region,
                    endpoint=azure_endpoint,
                    api_version=settings.translation_azure_api_version,
                ),
            )
        except Exception:
            logger.exception("backend_translation_startup_failed")
            set_runtime_field(app, "translation_error", "Failed to initialize Azure translation service.")
    else:
        logger.warning("backend_translation_startup_skipped_missing_azure_config")
        set_runtime_field(
            app,
            "translation_error",
            "Missing DANOTE_TRANSLATION_AZURE_API_KEY or DANOTE_TRANSLATION_AZURE_REGION.",
        )


def _override_or_setting(
    overrides: RuntimeApiKeyOverrides | None,
    field_name: str,
    setting_value: str | None,
) -> str | None:
    if overrides and field_name in overrides and overrides[field_name]:
        return overrides[field_name]
    return setting_value


def _close_service(service: object | None) -> None:
    close = getattr(service, "close", None)
    if callable(close):
        close()
