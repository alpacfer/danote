from __future__ import annotations

from fastapi import FastAPI

from app.api.schemas.v1 import DeveloperApiKeysUpdateRequest, DeveloperApiKeysUpdateResponse
from app.services.translation import AzureTranslationService
from app.services.tts import AzureSpeechTTSService
from app.services.verification import GeminiWordVerificationService


class DeveloperUseCase:
    def __init__(self, app: FastAPI):
        self._app = app

    def update_api_keys(self, payload: DeveloperApiKeysUpdateRequest) -> DeveloperApiKeysUpdateResponse:
        runtime_api_keys = {
            "translation_azure_api_key": (payload.translation_azure_api_key or "").strip() or None,
            "translation_azure_region": (payload.translation_azure_region or "").strip() or None,
            "translation_azure_endpoint": (payload.translation_azure_endpoint or "").strip() or None,
            "tts_azure_api_key": (payload.tts_azure_api_key or "").strip() or None,
            "tts_azure_region": (payload.tts_azure_region or "").strip() or None,
            "tts_azure_endpoint": (payload.tts_azure_endpoint or "").strip() or None,
            "word_verification_gemini": (payload.word_verification_gemini_api_key or "").strip() or None,
        }
        self._app.state.runtime_api_keys = runtime_api_keys

        translation_service = getattr(self._app.state, "translation_service", None)
        close = getattr(translation_service, "close", None)
        if callable(close):
            close()
        verification_service = getattr(self._app.state, "word_verification_service", None)
        verification_close = getattr(verification_service, "close", None)
        if callable(verification_close):
            verification_close()
        tts_service = getattr(self._app.state, "tts_service", None)
        tts_close = getattr(tts_service, "close", None)
        if callable(tts_close):
            tts_close()

        settings = self._app.state.settings
        self._app.state.translation_error = None
        self._app.state.translation_service = None
        if settings.translation_enabled:
            provider = settings.translation_provider.strip().lower()
            if provider == "azure":
                azure_key = runtime_api_keys["translation_azure_api_key"] or settings.translation_azure_api_key
                azure_region = runtime_api_keys["translation_azure_region"] or settings.translation_azure_region
                azure_endpoint = (
                    runtime_api_keys["translation_azure_endpoint"] or settings.translation_azure_endpoint
                )
                if azure_key and azure_region:
                    try:
                        self._app.state.translation_service = AzureTranslationService(
                            api_key=azure_key,
                            region=azure_region,
                            endpoint=azure_endpoint,
                            api_version=settings.translation_azure_api_version,
                        )
                    except Exception:
                        self._app.state.translation_error = "Failed to initialize Azure translation service."
                else:
                    self._app.state.translation_error = (
                        "Missing DANOTE_TRANSLATION_AZURE_API_KEY or DANOTE_TRANSLATION_AZURE_REGION."
                    )
            else:
                self._app.state.translation_error = f"Unknown translation provider '{provider}'."

        self._app.state.word_verification_error = None
        self._app.state.word_verification_service = None
        if settings.word_verification_enabled:
            verification_key = runtime_api_keys["word_verification_gemini"] or settings.word_verification_gemini_api_key
            if verification_key:
                try:
                    self._app.state.word_verification_service = GeminiWordVerificationService(
                        api_key=verification_key,
                        model=settings.word_verification_gemini_model,
                    )
                except Exception:
                    self._app.state.word_verification_error = "Failed to initialize Gemini word verification service."
            else:
                self._app.state.word_verification_error = "Missing DANOTE_WORD_VERIFICATION_GEMINI_API_KEY."

        self._app.state.tts_error = None
        self._app.state.tts_service = None
        if settings.tts_enabled:
            provider = settings.tts_provider.strip().lower()
            if provider == "azure":
                tts_key = runtime_api_keys["tts_azure_api_key"] or settings.tts_azure_api_key
                tts_region = runtime_api_keys["tts_azure_region"] or settings.tts_azure_region
                tts_endpoint = runtime_api_keys["tts_azure_endpoint"] or settings.tts_azure_endpoint
                if tts_key and tts_region:
                    try:
                        self._app.state.tts_service = AzureSpeechTTSService(
                            api_key=tts_key,
                            region=tts_region,
                            endpoint=tts_endpoint,
                            voice_name=settings.tts_azure_voice_name,
                        )
                    except Exception:
                        self._app.state.tts_error = "Failed to initialize Azure Speech TTS service."
                else:
                    self._app.state.tts_error = "Missing DANOTE_TTS_AZURE_API_KEY or DANOTE_TTS_AZURE_REGION."
            else:
                self._app.state.tts_error = f"Unknown TTS provider '{provider}'."

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
