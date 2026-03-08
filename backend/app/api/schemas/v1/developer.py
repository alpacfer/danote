from __future__ import annotations

from pydantic import BaseModel


class DeveloperApiKeysUpdateRequest(BaseModel):
    gemini_api_key: str | None = None
    translation_azure_api_key: str | None = None
    translation_azure_region: str | None = None
    translation_azure_endpoint: str | None = None
    tts_azure_api_key: str | None = None
    tts_azure_region: str | None = None
    tts_azure_endpoint: str | None = None
    word_verification_gemini_api_key: str | None = None


class DeveloperApiKeysUpdateResponse(BaseModel):
    status: str
    message: str
    configured: dict[str, bool]


class DeveloperServiceProbeResponse(BaseModel):
    status: str
    probe_input: str
    result_text: str | None = None
    provider: str | None = None
    message: str


class GeminiProbeResponse(DeveloperServiceProbeResponse):
    pass
