from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.api.schemas.v1.wordbank import WordActionSuggestion


class AnalyzeRequest(BaseModel):
    text: str = Field(...)


class AnalyzedToken(BaseModel):
    surface_token: str
    normalized_token: str
    lemma_candidate: str | None
    pos_tag: str | None = None
    morphology: str | None = None
    classification: Literal["known", "variation", "typo_likely", "uncertain", "new"]
    match_source: Literal["exact", "lemma", "none"]
    matched_lemma: str | None
    matched_surface_form: str | None
    suggestions: list[dict[str, object]] = Field(default_factory=list)
    confidence: float = 0.0
    reason_tags: list[str] = Field(default_factory=list)
    word_actions: list[WordActionSuggestion] = Field(default_factory=list)


class AnalyzeResponse(BaseModel):
    tokens: list[AnalyzedToken]


class EnrichTokenRequest(BaseModel):
    token: str = Field(..., min_length=1)
    include_translations: bool = True
    include_language_detection: bool = True

