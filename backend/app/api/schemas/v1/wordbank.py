from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AddWordRequest(BaseModel):
    surface_token: str = Field(..., min_length=1)
    lemma_candidate: str | None = None


class GenerateTranslationRequest(BaseModel):
    surface_token: str = Field(..., min_length=1)
    lemma_candidate: str | None = None


class GenerateTranslationResponse(BaseModel):
    status: Literal["generated", "unavailable"]
    source_word: str
    lemma: str
    english_translation: str | None


class AddWordResponse(BaseModel):
    status: Literal["inserted", "exists"]
    stored_lemma: str
    stored_surface_form: str | None
    source: Literal["manual"]
    message: str


class LemmaSummary(BaseModel):
    lemma: str
    english_translation: str | None
    variation_count: int


class LemmaListResponse(BaseModel):
    items: list[LemmaSummary]


class LemmaDetailsResponse(BaseModel):
    class SurfaceFormDetails(BaseModel):
        form: str
        english_translation: str | None

    lemma: str
    english_translation: str | None
    surface_forms: list[SurfaceFormDetails]


class ResetDatabaseResponse(BaseModel):
    status: Literal["reset"]
    message: str
