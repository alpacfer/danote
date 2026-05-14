from __future__ import annotations

from pydantic import BaseModel, Field


class AccountMeResponse(BaseModel):
    id: int
    email: str | None
    display_name: str | None
    auth_provider: str


class ApiKeyStatus(BaseModel):
    provider: str
    is_set: bool
    last_four: str | None = None


class AccountStatusResponse(BaseModel):
    keys_configured: bool
    providers: dict[str, ApiKeyStatus]
    missing: list[str]


class UpdateApiKeyRequest(BaseModel):
    value: str = Field(min_length=1, max_length=2048)


class UpdateApiKeyResponse(BaseModel):
    provider: str
    is_set: bool
    last_four: str | None


class TestApiKeyResponse(BaseModel):
    provider: str
    ok: bool
    error: str | None = None
