from __future__ import annotations

from fastapi import FastAPI

from app.api.schemas.v1 import DeveloperApiKeysUpdateRequest, DeveloperApiKeysUpdateResponse
from app.services.translation import DeepLTranslationService, GeminiTranslationService
from app.services.tts import GeminiTTSService
from app.services.verification import GeminiWordVerificationService


class DeveloperUseCase:
    def __init__(self, app: FastAPI):
        self._app = app

    def update_api_keys(self, payload: DeveloperApiKeysUpdateRequest) -> DeveloperApiKeysUpdateResponse:
        runtime_api_keys = {
            "gemini": (payload.gemini_api_key or "").strip() or None,
            "deepl": (payload.deepl_api_key or "").strip() or None,
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
            if provider == "gemini":
                gemini_key = runtime_api_keys["gemini"] or settings.translation_gemini_api_key
                if gemini_key:
                    try:
                        self._app.state.translation_service = GeminiTranslationService(
                            api_key=gemini_key,
                            model=settings.translation_gemini_model,
                        )
                    except Exception:
                        self._app.state.translation_error = "Failed to initialize Gemini translation service."
                else:
                    self._app.state.translation_error = "Missing DANOTE_GEMINI_API_KEY."
            elif provider == "deepl":
                deepl_key = runtime_api_keys["deepl"] or settings.translation_deepl_api_key
                if deepl_key:
                    try:
                        self._app.state.translation_service = DeepLTranslationService(
                            api_key=deepl_key,
                            base_url=settings.translation_deepl_api_url,
                        )
                    except Exception:
                        self._app.state.translation_error = "Failed to initialize DeepL translation service."
                else:
                    self._app.state.translation_error = "Missing DANOTE_DEEPL_API_KEY."
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
            if provider == "gemini":
                tts_key = runtime_api_keys["gemini"] or settings.tts_gemini_api_key
                if tts_key:
                    try:
                        self._app.state.tts_service = GeminiTTSService(
                            api_key=tts_key,
                            model=settings.tts_gemini_model,
                            voice_name=settings.tts_gemini_voice_name,
                        )
                    except Exception:
                        self._app.state.tts_error = "Failed to initialize Gemini TTS service."
                else:
                    self._app.state.tts_error = "Missing DANOTE_TTS_GEMINI_API_KEY."
            else:
                self._app.state.tts_error = f"Unknown TTS provider '{provider}'."

        return DeveloperApiKeysUpdateResponse(
            status="updated",
            message="Runtime API keys updated.",
            configured={
                "gemini": bool(runtime_api_keys["gemini"] or settings.translation_gemini_api_key),
                "deepl": bool(runtime_api_keys["deepl"] or settings.translation_deepl_api_key),
                "word_verification_gemini": bool(
                    runtime_api_keys["word_verification_gemini"] or settings.word_verification_gemini_api_key
                ),
            },
        )
