from __future__ import annotations

from pydantic import BaseModel


class DeveloperApiKeysUpdateRequest(BaseModel):
    gemini_api_key: str | None = None
    deepl_api_key: str | None = None
    word_verification_gemini_api_key: str | None = None


class DeveloperApiKeysUpdateResponse(BaseModel):
    status: str
    message: str
    configured: dict[str, bool]
