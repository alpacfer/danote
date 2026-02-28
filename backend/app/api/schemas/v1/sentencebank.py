from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AddSentenceRequest(BaseModel):
    source_text: str = Field(..., min_length=1)


class AddSentenceResponse(BaseModel):
    status: Literal["inserted", "exists"]
    source_text: str
    english_translation: str | None
    message: str


class SentenceSummary(BaseModel):
    id: int
    source_text: str
    english_translation: str | None
    created_at: str


class SentenceListResponse(BaseModel):
    items: list[SentenceSummary]
