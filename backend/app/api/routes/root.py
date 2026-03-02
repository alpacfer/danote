from fastapi import APIRouter, Request

from app.api.schemas.v1 import HealthResponse

router = APIRouter()


@router.get("/")
def api_root() -> dict[str, str]:
    return {"status": "ok", "message": "danote backend scaffold"}


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    db_ready = bool(getattr(request.app.state, "db_ready", False))
    nlp_ready = bool(getattr(request.app.state, "nlp_ready", False))
    status = "ok" if db_ready and nlp_ready else "degraded"
    translation_enabled = bool(getattr(settings, "translation_enabled", False))
    translation_service = getattr(request.app.state, "translation_service", None)
    translation_provider_selected = str(getattr(settings, "translation_provider", "") or "").strip().lower()
    active_translation_provider = str(getattr(translation_service, "provider", "") or "").strip().lower()

    runtime_api_keys = getattr(request.app.state, "runtime_api_keys", {}) or {}
    translator_key = runtime_api_keys.get("translation_azure_api_key") or getattr(
        settings, "translation_azure_api_key", ""
    )
    translator_region = runtime_api_keys.get("translation_azure_region") or getattr(
        settings, "translation_azure_region", ""
    )
    translator_key_configured = bool(str(translator_key or "").strip() and str(translator_region or "").strip())
    translation_error = getattr(request.app.state, "translation_error", None)
    translation_component_status = (
        "disabled"
        if not translation_enabled
        else "ok" if translation_service is not None else "degraded"
    )

    tts_enabled = bool(getattr(settings, "tts_enabled", False))
    tts_service = getattr(request.app.state, "tts_service", None)
    tts_provider_selected = str(getattr(settings, "tts_provider", "") or "").strip().lower()
    active_tts_provider = str(getattr(tts_service, "provider", "") or "").strip().lower()
    tts_key = runtime_api_keys.get("tts_azure_api_key") or getattr(settings, "tts_azure_api_key", "")
    tts_region = runtime_api_keys.get("tts_azure_region") or getattr(settings, "tts_azure_region", "")
    tts_key_configured = bool(str(tts_key or "").strip() and str(tts_region or "").strip())
    tts_error = getattr(request.app.state, "tts_error", None)
    tts_component_status = "disabled" if not tts_enabled else "ok" if tts_service is not None else "degraded"

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
    ) -> dict[str, object]:
        if not service_enabled:
            return {
                "status": "disabled",
                "active": False,
                "configured": key_configured,
                "message": disabled_message,
            }

        if selected_provider != provider_name:
            return {
                "status": "inactive",
                "active": False,
                "configured": key_configured,
                "message": f"Provider '{provider_name}' is not selected.",
            }

        if active_provider in active_provider_names and service is not None:
            return {
                "status": "ok",
                "active": True,
                "configured": key_configured,
                "message": None,
            }

        if not key_configured:
            return {
                "status": "missing_key",
                "active": False,
                "configured": False,
                "message": missing_key_message,
            }

        return {
            "status": "degraded",
            "active": False,
            "configured": True,
            "message": str(error) if error else f"Provider '{provider_name}' failed to initialize.",
        }

    payload: dict[str, object] = {
        "status": status,
        "service": "backend",
        "components": {
            "database": "ok" if db_ready else "degraded",
            "nlp": "ok" if nlp_ready else "degraded",
            "translation": translation_component_status,
            "tts": tts_component_status,
        },
        "apis": {
            "backend": {
                "status": "ok" if status == "ok" else "degraded",
                "active": True,
                "configured": True,
                "message": None,
            },
            "azure_translator": _provider_status(
                provider_name="azure",
                selected_provider=translation_provider_selected,
                active_provider=active_translation_provider,
                active_provider_names={"azure_translator"},
                service_enabled=translation_enabled,
                key_configured=translator_key_configured,
                service=translation_service,
                error=translation_error,
                disabled_message="Translation is disabled.",
                missing_key_message="Missing DANOTE_TRANSLATION_AZURE_API_KEY or DANOTE_TRANSLATION_AZURE_REGION.",
            ),
            "azure_speech": _provider_status(
                provider_name="azure",
                selected_provider=tts_provider_selected,
                active_provider=active_tts_provider,
                active_provider_names={"azure_speech_tts"},
                service_enabled=tts_enabled,
                key_configured=tts_key_configured,
                service=tts_service,
                error=tts_error,
                disabled_message="Text-to-speech is disabled.",
                missing_key_message="Missing DANOTE_TTS_AZURE_API_KEY or DANOTE_TTS_AZURE_REGION.",
            ),
        },
    }

    db_error = getattr(request.app.state, "db_error", None)
    nlp_error = getattr(request.app.state, "nlp_error", None)
    if db_error:
        payload["db_error"] = str(db_error)
    if nlp_error:
        payload["nlp_error"] = str(nlp_error)
    if translation_error:
        payload["translation_error"] = str(translation_error)
    if tts_error:
        payload["tts_error"] = str(tts_error)

    return HealthResponse.model_validate(payload)
