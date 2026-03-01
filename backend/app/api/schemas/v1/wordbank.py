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


class GenerateReverseTranslationRequest(BaseModel):
    source_word: str = Field(..., min_length=1)


class GenerateReverseTranslationResponse(BaseModel):
    status: Literal["generated", "unavailable"]
    source_word: str
    danish_translation: str | None


class DetectWordLanguageRequest(BaseModel):
    source_word: str = Field(..., min_length=1)


class DetectWordLanguageResponse(BaseModel):
    source_word: str
    language: Literal["en", "da", "ambiguous"]
    confidence: float


class GeneratePhraseTranslationRequest(BaseModel):
    source_text: str = Field(..., min_length=1)


class GeneratePhraseTranslationResponse(BaseModel):
    status: Literal["generated", "cached", "unavailable"]
    source_text: str
    english_translation: str | None


class AddWordResponse(BaseModel):
    class VerificationResult(BaseModel):
        status: Literal["verified", "flagged", "error", "skipped", "queued"]
        provider: str | None = None
        reviewer_role: str | None = None
        message: str
        composed_word_count: int | None = None

    status: Literal["inserted", "exists"]
    stored_lemma: str
    stored_surface_form: str | None
    source: Literal["manual"]
    message: str
    verification: VerificationResult | None = None


class VerifyWordRequest(BaseModel):
    stored_lemma: str = Field(..., min_length=1)
    stored_surface_form: str | None = None


class VerifyWordResponse(BaseModel):
    stored_lemma: str
    stored_surface_form: str | None
    verification: AddWordResponse.VerificationResult


class LemmaSummary(BaseModel):
    lemma: str
    display_lemma: str
    english_translation: str | None
    variation_count: int


class LemmaListResponse(BaseModel):
    items: list[LemmaSummary]


class LemmaDetailsResponse(BaseModel):
    pos_tag: str | None = None
    morphology: str | None = None

    class SurfaceFormDetails(BaseModel):
        form: str
        english_translation: str | None
        pos_tag: str | None = None
        morphology: str | None = None

    lemma: str
    english_translation: str | None
    surface_forms: list[SurfaceFormDetails]


class ResetDatabaseResponse(BaseModel):
    status: Literal["reset"]
    message: str
