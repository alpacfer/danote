from __future__ import annotations

from app.api.schemas.v1 import ApiStatusEntry, HealthResponse
from app.core.app_state import BackendRuntimeState


def build_health_status(runtime: BackendRuntimeState) -> HealthResponse:
    settings = runtime.settings
    services = runtime.services
    runtime_api_keys = runtime.runtime_api_keys or {}

    nlp_enabled = bool(getattr(settings, "nlp_enabled", True))
    translation_enabled = bool(getattr(settings, "translation_enabled", False))
    tts_enabled = bool(getattr(settings, "tts_enabled", False))

    translation_service = services.translation_service
    tts_service = services.tts_service
    gemini_word_translation_service = services.gemini_word_translation_service
    gemini_verification_service = services.word_verification_service

    status = "ok" if runtime.db_ready and ((not nlp_enabled) or runtime.nlp_ready) else "degraded"

    translation_provider_selected = _normalize_provider(
        runtime_api_keys.get("translation_provider") or getattr(settings, "translation_provider", "")
    )
    active_translation_provider = _normalize_provider(getattr(translation_service, "provider", ""))

    tts_provider_selected = _normalize_provider(getattr(settings, "tts_provider", ""))
    active_tts_provider = _normalize_provider(getattr(tts_service, "provider", ""))

    payload = HealthResponse(
        status=status,
        service="backend",
        components={
            "database": "ok" if runtime.db_ready else "degraded",
            "nlp": "disabled" if not nlp_enabled else ("ok" if runtime.nlp_ready else "degraded"),
            "translation": "disabled" if not translation_enabled else ("ok" if translation_service else "degraded"),
            "tts": "disabled" if not tts_enabled else ("ok" if tts_service else "degraded"),
        },
        apis={
            "backend": ApiStatusEntry(status="ok" if status == "ok" else "degraded", active=True, configured=True),
            "azure_translator": _provider_status(
                provider_name="azure",
                selected_provider=translation_provider_selected,
                active_provider=active_translation_provider,
                active_provider_names={"azure_translator"},
                service_enabled=translation_enabled,
                key_configured=_azure_translation_key_configured(runtime),
                service=translation_service,
                error=runtime.translation_error,
                disabled_message="Translation is disabled.",
                missing_key_message="Missing DANOTE_TRANSLATION_AZURE_API_KEY or DANOTE_TRANSLATION_AZURE_REGION.",
            ),
            "deepl_translator": _provider_status(
                provider_name="deepl",
                selected_provider=translation_provider_selected,
                active_provider=active_translation_provider,
                active_provider_names={"deepl_translator"},
                service_enabled=translation_enabled,
                key_configured=_deepl_translation_key_configured(runtime),
                service=translation_service,
                error=runtime.translation_error,
                disabled_message="Translation is disabled.",
                missing_key_message="Missing DANOTE_TRANSLATION_DEEPL_API_KEY.",
            ),
            "azure_speech": _provider_status(
                provider_name="azure",
                selected_provider=tts_provider_selected,
                active_provider=active_tts_provider,
                active_provider_names={"azure_speech_tts"},
                service_enabled=tts_enabled,
                key_configured=_azure_tts_key_configured(runtime),
                service=tts_service,
                error=runtime.tts_error,
                disabled_message="Text-to-speech is disabled.",
                missing_key_message="Missing DANOTE_TTS_AZURE_API_KEY or DANOTE_TTS_AZURE_REGION.",
            ),
            "gemini": _gemini_status(runtime),
        },
        db_error=str(runtime.db_error) if runtime.db_error else None,
        nlp_error=str(runtime.nlp_error) if runtime.nlp_error else None,
        translation_error=str(runtime.translation_error) if runtime.translation_error else None,
        tts_error=str(runtime.tts_error) if runtime.tts_error else None,
    )
    return payload


def _provider_status(
    *,
    provider_name: str,
    selected_provider: str,
    active_provider: str,
    active_provider_names: set[str],
    service_enabled: bool,
    key_configured: bool,
    service: object | None,
    error: object | None,
    disabled_message: str,
    missing_key_message: str,
) -> ApiStatusEntry:
    if not service_enabled:
        return ApiStatusEntry(status="disabled", configured=key_configured, message=disabled_message)

    if selected_provider != provider_name:
        return ApiStatusEntry(
            status="inactive",
            configured=key_configured,
            message=f"Provider '{provider_name}' is not selected.",
        )

    if active_provider in active_provider_names and service is not None:
        return ApiStatusEntry(status="ok", active=True, configured=key_configured)

    if not key_configured:
        return ApiStatusEntry(status="missing_key", configured=False, message=missing_key_message)

    return ApiStatusEntry(
        status="degraded",
        configured=True,
        message=str(error) if error else f"Provider '{provider_name}' failed to initialize.",
    )


def _gemini_status(runtime: BackendRuntimeState) -> ApiStatusEntry:
    settings = runtime.settings
    runtime_api_keys = runtime.runtime_api_keys or {}
    gemini_key = runtime_api_keys.get("gemini_api_key") or getattr(settings, "gemini_api_key", "")
    gemini_key_configured = bool(str(gemini_key or "").strip())
    service_ready = (
        runtime.services.gemini_word_translation_service is not None
        or runtime.services.word_verification_service is not None
    )
    if service_ready:
        return ApiStatusEntry(status="ok", active=True, configured=gemini_key_configured)
    if not gemini_key_configured:
        return ApiStatusEntry(status="missing_key", configured=False, message="Missing DANOTE_GEMINI_API_KEY.")
    return ApiStatusEntry(
        status="degraded",
        configured=True,
        message=str(runtime.gemini_word_translation_error or runtime.word_verification_error or ""),
    )


def _normalize_provider(value: object) -> str:
    return str(value or "").strip().lower()


def _azure_translation_key_configured(runtime: BackendRuntimeState) -> bool:
    settings = runtime.settings
    runtime_api_keys = runtime.runtime_api_keys or {}
    key = runtime_api_keys.get("translation_azure_api_key") or getattr(settings, "translation_azure_api_key", "")
    region = runtime_api_keys.get("translation_azure_region") or getattr(settings, "translation_azure_region", "")
    return bool(str(key or "").strip() and str(region or "").strip())


def _deepl_translation_key_configured(runtime: BackendRuntimeState) -> bool:
    settings = runtime.settings
    runtime_api_keys = runtime.runtime_api_keys or {}
    key = runtime_api_keys.get("translation_deepl_api_key") or getattr(settings, "translation_deepl_api_key", "")
    return bool(str(key or "").strip())


def _azure_tts_key_configured(runtime: BackendRuntimeState) -> bool:
    settings = runtime.settings
    runtime_api_keys = runtime.runtime_api_keys or {}
    key = runtime_api_keys.get("tts_azure_api_key") or getattr(settings, "tts_azure_api_key", "")
    region = runtime_api_keys.get("tts_azure_region") or getattr(settings, "tts_azure_region", "")
    return bool(str(key or "").strip() and str(region or "").strip())
