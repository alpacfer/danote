from __future__ import annotations

import logging

from fastapi import FastAPI

from app.core.app_state import get_runtime_state, set_runtime_field, set_service_field
from app.core.config import Settings
from app.services.deepl_translation import DeepLTranslationService
from app.services.translation import AzureTranslationService, TranslationError

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

    provider = _selected_provider(settings, overrides)
    if provider not in {"azure", "deepl"}:
        logger.warning(
            "backend_translation_startup_skipped_unknown_provider",
            extra={"translation_provider": provider},
        )
        set_runtime_field(app, "translation_error", f"Unknown translation provider '{provider}'.")
        return

    if provider == "azure":
        _initialize_azure(app, settings, overrides)
        return
    _initialize_deepl(app, settings, overrides)


def _override_or_setting(
    overrides: RuntimeApiKeyOverrides | None,
    field_name: str,
    setting_value: str | None,
) -> str | None:
    if overrides and field_name in overrides and overrides[field_name]:
        return overrides[field_name]
    return setting_value


def _selected_provider(
    settings: Settings,
    overrides: RuntimeApiKeyOverrides | None,
) -> str:
    override_provider = _override_or_setting(overrides, "translation_provider", None)
    if override_provider:
        return override_provider.strip().lower()
    return settings.translation_provider.strip().lower()


def _log_startup_failure(*, provider: str, operation: str, exc: Exception) -> None:
    logger.warning(
        "backend_translation_startup_failed",
        extra={
            "provider": provider,
            "operation": operation,
            "failure_class": exc.__class__.__name__,
            "retryable": False,
        },
        exc_info=exc,
    )


def _initialize_azure(
    app: FastAPI,
    settings: Settings,
    overrides: RuntimeApiKeyOverrides | None,
) -> None:
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
        except (TranslationError, ValueError, TypeError) as exc:
            _log_startup_failure(provider="azure_translator", operation="startup.initialize", exc=exc)
            set_runtime_field(app, "translation_error", "Failed to initialize Azure translation service.")
    else:
        logger.warning("backend_translation_startup_skipped_missing_azure_config")
        set_runtime_field(
            app,
            "translation_error",
            "Missing DANOTE_TRANSLATION_AZURE_API_KEY or DANOTE_TRANSLATION_AZURE_REGION.",
        )


def _initialize_deepl(
    app: FastAPI,
    settings: Settings,
    overrides: RuntimeApiKeyOverrides | None,
) -> None:
    deepl_key = _override_or_setting(overrides, "translation_deepl_api_key", settings.translation_deepl_api_key)
    deepl_endpoint = _override_or_setting(overrides, "translation_deepl_endpoint", settings.translation_deepl_endpoint)
    if deepl_key:
        try:
            set_service_field(
                app,
                "translation_service",
                DeepLTranslationService(
                    api_key=deepl_key,
                    endpoint=deepl_endpoint,
                ),
            )
        except (TranslationError, ValueError, TypeError) as exc:
            _log_startup_failure(provider="deepl_translator", operation="startup.initialize", exc=exc)
            set_runtime_field(app, "translation_error", "Failed to initialize DeepL translation service.")
    else:
        logger.warning("backend_translation_startup_skipped_missing_deepl_config")
        set_runtime_field(
            app,
            "translation_error",
            "Missing DANOTE_TRANSLATION_DEEPL_API_KEY.",
        )


def _close_service(service: object | None) -> None:
    close = getattr(service, "close", None)
    if callable(close):
        close()
