from __future__ import annotations

from pydantic import BaseModel, Field

from app.api.schemas.v1.account import TrialStatus


class GuestSessionRequest(BaseModel):
    browser_id: str = Field(min_length=8, max_length=256)


class GuestSessionResponse(BaseModel):
    token: str
    auth_provider: str
    trial: TrialStatus
