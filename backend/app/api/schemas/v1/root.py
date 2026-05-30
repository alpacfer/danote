from __future__ import annotations

from pydantic import BaseModel


class ApiStatusEntry(BaseModel):
    status: str
    active: bool = False
    configured: bool = False
    message: str | None = None


class HealthResponse(BaseModel):
    status: str
    service: str
    components: dict[str, str]
    apis: dict[str, ApiStatusEntry]
    db_error: str | None = None
    nlp_error: str | None = None
    translation_error: str | None = None
    tts_error: str | None = None
    memory_usage_kb: int | None = None
