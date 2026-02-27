from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    text: str = Field(...)


class AnalyzedToken(BaseModel):
    surface_token: str
    normalized_token: str
    lemma_candidate: str | None
    classification: Literal["known", "variation", "typo_likely", "uncertain", "new"]
    match_source: Literal["exact", "lemma", "none"]
    matched_lemma: str | None
    matched_surface_form: str | None
    suggestions: list[dict[str, object]] = Field(default_factory=list)
    confidence: float = 0.0
    reason_tags: list[str] = Field(default_factory=list)
    pos_tag: str | None = None
    morphology: str | None = None

    # v1-friendly aliases
    status: Literal["known", "variation", "typo_likely", "uncertain", "new"]
    surface: str
    normalized: str
    lemma: str | None


class AnalyzeResponse(BaseModel):
    tokens: list[AnalyzedToken]
