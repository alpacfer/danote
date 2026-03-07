from __future__ import annotations

from fastapi import FastAPI

from app.api.schemas.v1 import DeveloperApiKeysUpdateRequest, DeveloperApiKeysUpdateResponse
from app.bootstrap.runtime_translation import RuntimeApiKeyOverrides, initialize_translation
from app.bootstrap.runtime_tts import initialize_tts
from app.bootstrap.runtime_word_verification import initialize_word_verification
from app.core.app_state import get_runtime_state, set_runtime_field


class DeveloperUseCase:
    def __init__(self, app: FastAPI):
        self._app = app

    def update_api_keys(self, payload: DeveloperApiKeysUpdateRequest) -> DeveloperApiKeysUpdateResponse:
        runtime = get_runtime_state(self._app)
        runtime_api_keys: RuntimeApiKeyOverrides = {
            "translation_azure_api_key": (payload.translation_azure_api_key or "").strip() or None,
            "translation_azure_region": (payload.translation_azure_region or "").strip() or None,
            "translation_azure_endpoint": (payload.translation_azure_endpoint or "").strip() or None,
            "tts_azure_api_key": (payload.tts_azure_api_key or "").strip() or None,
            "tts_azure_region": (payload.tts_azure_region or "").strip() or None,
            "tts_azure_endpoint": (payload.tts_azure_endpoint or "").strip() or None,
            "word_verification_gemini": (payload.word_verification_gemini_api_key or "").strip() or None,
        }
        set_runtime_field(self._app, "runtime_api_keys", runtime_api_keys)

        settings = runtime.settings
        initialize_translation(self._app, settings, runtime_api_keys)
        initialize_word_verification(self._app, settings, runtime_api_keys)
        initialize_tts(self._app, settings, runtime_api_keys)

        return DeveloperApiKeysUpdateResponse(
            status="updated",
            message="Runtime API keys updated.",
            configured={
                "translation_azure": bool(
                    (runtime_api_keys["translation_azure_api_key"] or settings.translation_azure_api_key)
                    and (runtime_api_keys["translation_azure_region"] or settings.translation_azure_region)
                ),
                "tts_azure": bool(
                    (runtime_api_keys["tts_azure_api_key"] or settings.tts_azure_api_key)
                    and (runtime_api_keys["tts_azure_region"] or settings.tts_azure_region)
                ),
                "word_verification_gemini": bool(
                    runtime_api_keys["word_verification_gemini"] or settings.word_verification_gemini_api_key
                ),
            },
        )
