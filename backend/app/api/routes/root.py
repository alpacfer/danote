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
    selected_provider_raw = str(getattr(settings, "translation_provider", "") or "").strip().lower()
    translation_service = getattr(request.app.state, "translation_service", None)
    active_provider_raw = str(getattr(translation_service, "provider", "") or "").strip().lower()

    gemini_key_configured = bool(str(getattr(settings, "translation_gemini_api_key", "") or "").strip())
    deepl_key_configured = bool(str(getattr(settings, "translation_deepl_api_key", "") or "").strip())
    translation_error = getattr(request.app.state, "translation_error", None)
    translation_component_status = (
        "disabled"
        if not translation_enabled
        else "ok" if translation_service is not None else "degraded"
    )

    def _provider_status(provider_name: str, key_configured: bool) -> dict[str, object]:
        if not translation_enabled:
            return {
                "status": "disabled",
                "active": False,
                "configured": key_configured,
                "message": "Translation is disabled.",
            }

        if selected_provider_raw != provider_name:
            return {
                "status": "inactive",
                "active": False,
                "configured": key_configured,
                "message": f"Provider '{provider_name}' is not selected.",
            }

        if active_provider_raw == provider_name and translation_service is not None:
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
                "message": f"Missing key for provider '{provider_name}'.",
            }

        return {
            "status": "degraded",
            "active": False,
            "configured": True,
            "message": str(translation_error) if translation_error else f"Provider '{provider_name}' failed to initialize.",
        }

    payload: dict[str, object] = {
        "status": status,
        "service": "backend",
        "components": {
            "database": "ok" if db_ready else "degraded",
            "nlp": "ok" if nlp_ready else "degraded",
            "translation": translation_component_status,
        },
        "apis": {
            "backend": {
                "status": "ok" if status == "ok" else "degraded",
                "active": True,
                "configured": True,
                "message": None,
            },
            "gemini": _provider_status("gemini", gemini_key_configured),
            "deepl": _provider_status("deepl", deepl_key_configured),
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

    return HealthResponse.model_validate(payload)
