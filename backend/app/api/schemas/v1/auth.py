from __future__ import annotations

from pydantic import BaseModel


class CurrentUserResponse(BaseModel):
    id: int
    auth_provider: str
    auth_subject: str
    email: str | None = None
    display_name: str | None = None
    created_at: str
    last_seen_at: str
