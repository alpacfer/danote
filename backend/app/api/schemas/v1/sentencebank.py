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


class SentenceVerificationErrorItem(BaseModel):
    start: int
    end: int
    message: str


class VerifySentenceRequest(BaseModel):
    source_text: str = Field(..., min_length=1, max_length=100)


class VerifySentenceResponse(BaseModel):
    is_valid: bool
    errors: list[SentenceVerificationErrorItem] = Field(default_factory=list)
    corrected_text: str | None = None
    language: Literal["da", "en", "unknown"] = "unknown"


class SentenceSearchPreviewRequest(BaseModel):
    source_text: str = Field(..., min_length=1, max_length=100)
    fast: bool = False


class SentenceSearchPreviewResponse(BaseModel):
    status: Literal["ready", "blocked", "preview"]
    query_language: Literal["da", "en", "unknown"] = "unknown"
    source_text: str | None = None
    english_translation: str | None = None
    is_valid: bool
    errors: list[SentenceVerificationErrorItem] = Field(default_factory=list)
    message: str | None = None
