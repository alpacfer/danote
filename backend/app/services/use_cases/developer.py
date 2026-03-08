from __future__ import annotations

from fastapi import FastAPI

from app.api.schemas.v1 import (
    DeveloperApiKeysUpdateRequest,
    DeveloperApiKeysUpdateResponse,
    DeveloperServiceProbeResponse,
    GeminiProbeResponse,
)
from app.bootstrap.runtime_gemini_word_translation import initialize_gemini_word_translation
from app.bootstrap.runtime_translation import RuntimeApiKeyOverrides, initialize_translation
from app.bootstrap.runtime_tts import initialize_tts
from app.bootstrap.runtime_word_verification import initialize_word_verification
from app.core.app_state import get_runtime_state, set_runtime_field
from app.services.gemini_translation import ContextualWordTranslationInput


class DeveloperUseCase:
    def __init__(self, app: FastAPI):
        self._app = app

    def update_api_keys(self, payload: DeveloperApiKeysUpdateRequest) -> DeveloperApiKeysUpdateResponse:
        runtime = get_runtime_state(self._app)
        runtime_api_keys: RuntimeApiKeyOverrides = {
            "gemini_api_key": (payload.gemini_api_key or "").strip() or None,
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
        initialize_gemini_word_translation(self._app, settings, runtime_api_keys)
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
                "gemini": bool(runtime_api_keys["gemini_api_key"] or settings.gemini_api_key),
                "word_verification_gemini": bool(
                    runtime_api_keys["word_verification_gemini"]
                    or settings.word_verification_gemini_api_key
                    or runtime_api_keys["gemini_api_key"]
                    or settings.gemini_api_key
                ),
            },
        )

    def run_gemini_probe(self) -> GeminiProbeResponse:
        runtime = get_runtime_state(self._app)
        service = runtime.services.gemini_word_translation_service
        probe_input = "bogen"
        if service is None:
            probe_response = self._missing_service_probe_response(
                probe_input=probe_input,
                error_message=runtime.gemini_word_translation_error,
                fallback_message="Gemini word translation is unavailable.",
            )
            return GeminiProbeResponse(**probe_response.model_dump())

        try:
            result_text = service.translate_word(
                ContextualWordTranslationInput(
                    surface_form="bogen",
                    lemma="bog",
                    gloss="book",
                )
            )
        except Exception as exc:
            probe_response = self._error_probe_response(
                probe_input=probe_input,
                provider=getattr(service, "provider", None),
                message=str(exc),
            )
            return GeminiProbeResponse(**probe_response.model_dump())

        if not result_text:
            probe_response = self._error_probe_response(
                probe_input=probe_input,
                provider=getattr(service, "provider", None),
                message="Gemini returned no translation for the probe input.",
            )
            return GeminiProbeResponse(**probe_response.model_dump())

        return GeminiProbeResponse(
            status="ok",
            probe_input=probe_input,
            provider=getattr(service, "provider", None),
            result_text=result_text,
            message="Gemini probe completed successfully.",
        )

    def run_translation_probe(self) -> DeveloperServiceProbeResponse:
        runtime = get_runtime_state(self._app)
        service = runtime.services.translation_service
        probe_input = "bogen"
        if service is None:
            return self._missing_service_probe_response(
                probe_input=probe_input,
                error_message=runtime.translation_error,
                fallback_message="Azure translation is unavailable.",
            )

        try:
            result_text = service.translate_da_to_en(probe_input)
        except Exception as exc:
            return self._error_probe_response(
                probe_input=probe_input,
                provider=getattr(service, "provider", None),
                message=str(exc),
            )

        if not result_text:
            return self._error_probe_response(
                probe_input=probe_input,
                provider=getattr(service, "provider", None),
                message="Azure Translator returned no translation for the probe input.",
            )

        return DeveloperServiceProbeResponse(
            status="ok",
            probe_input=probe_input,
            provider=getattr(service, "provider", None),
            result_text=result_text,
            message="Azure Translator probe completed successfully.",
        )

    def run_tts_probe(self) -> DeveloperServiceProbeResponse:
        runtime = get_runtime_state(self._app)
        service = runtime.services.tts_service
        probe_input = "bogen"
        if service is None:
            return self._missing_service_probe_response(
                probe_input=probe_input,
                error_message=runtime.tts_error,
                fallback_message="Azure Speech is unavailable.",
            )

        try:
            audio = service.synthesize(probe_input)
        except Exception as exc:
            return self._error_probe_response(
                probe_input=probe_input,
                provider=getattr(service, "provider", None),
                message=str(exc),
            )

        if audio is None or not getattr(audio, "audio_bytes", b""):
            return self._error_probe_response(
                probe_input=probe_input,
                provider=getattr(service, "provider", None),
                message="Azure Speech returned no audio for the probe input.",
            )

        audio_bytes = bytes(getattr(audio, "audio_bytes", b""))
        mime_type = str(getattr(audio, "mime_type", "audio/wav") or "audio/wav")
        return DeveloperServiceProbeResponse(
            status="ok",
            probe_input=probe_input,
            provider=getattr(service, "provider", None),
            result_text=f"{mime_type} ({len(audio_bytes)} bytes)",
            message="Azure Speech probe completed successfully.",
        )

    def _missing_service_probe_response(
        self,
        *,
        probe_input: str,
        error_message: str | None,
        fallback_message: str,
    ) -> DeveloperServiceProbeResponse:
        return DeveloperServiceProbeResponse(
            status="error",
            probe_input=probe_input,
            provider=None,
            result_text=None,
            message=error_message or fallback_message,
        )

    def _error_probe_response(
        self,
        *,
        probe_input: str,
        provider: str | None,
        message: str,
    ) -> DeveloperServiceProbeResponse:
        return DeveloperServiceProbeResponse(
            status="error",
            probe_input=probe_input,
            provider=provider,
            result_text=None,
            message=message,
        )
