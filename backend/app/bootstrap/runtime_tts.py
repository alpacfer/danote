from __future__ import annotations

import logging

from fastapi import FastAPI

from app.bootstrap.runtime_translation import RuntimeApiKeyOverrides
from app.core.app_state import get_runtime_state, set_runtime_field, set_service_field
from app.core.config import Settings
from app.services.tts import AzureSpeechTTSService

logger = logging.getLogger(__name__)


def initialize_tts(
    app: FastAPI,
    settings: Settings,
    overrides: RuntimeApiKeyOverrides | None = None,
) -> None:
    set_runtime_field(app, "tts_error", None)
    _close_service(get_runtime_state(app).services.tts_service)
    set_service_field(app, "tts_service", None)
    if not settings.tts_enabled:
        return

    provider = settings.tts_provider.strip().lower()
    if provider != "azure":
        logger.warning(
            "backend_tts_startup_skipped_unknown_provider",
            extra={"tts_provider": provider},
        )
        set_runtime_field(app, "tts_error", f"Unknown TTS provider '{provider}'.")
        return

    tts_key = _override_or_setting(overrides, "tts_azure_api_key", settings.tts_azure_api_key)
    tts_region = _override_or_setting(overrides, "tts_azure_region", settings.tts_azure_region)
    tts_endpoint = _override_or_setting(overrides, "tts_azure_endpoint", settings.tts_azure_endpoint)

    if tts_key and tts_region:
        try:
            set_service_field(
                app,
                "tts_service",
                AzureSpeechTTSService(
                    api_key=tts_key,
                    region=tts_region,
                    endpoint=tts_endpoint,
                    voice_name=settings.tts_azure_voice_name,
                ),
            )
        except Exception:
            logger.exception("backend_tts_startup_failed")
            set_runtime_field(app, "tts_error", "Failed to initialize Azure Speech TTS service.")
    else:
        logger.warning("backend_tts_startup_skipped_missing_azure_config")
        set_runtime_field(
            app,
            "tts_error",
            "Missing DANOTE_TTS_AZURE_API_KEY or DANOTE_TTS_AZURE_REGION.",
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
