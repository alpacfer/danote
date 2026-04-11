from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AddSentenceRequest(BaseModel):
    source_text: str = Field(..., min_length=1)


class SentenceTokenCard(BaseModel):
    token_index: int
    surface_form: str
    stored_lemma: str
    lexeme_id: int
    meaning_id: int | None = None
    pos_tag: str | None = None
    morphology: str | None = None
    gloss: str | None = None
    english_translation: str | None = None
    gloss_translation: str | None = None


class SentenceSummary(BaseModel):
    id: int
    source_text: str
    english_translation: str | None
    created_at: str
    tokens: list[SentenceTokenCard] = Field(default_factory=list)


class AddSentenceResponse(SentenceSummary):
    status: Literal["inserted", "exists"]
    message: str


class SentenceListResponse(BaseModel):
    items: list[SentenceSummary]
