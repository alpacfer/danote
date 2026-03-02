from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AddWordRequest(BaseModel):
    surface_token: str = Field(..., min_length=1)
    lemma_candidate: str | None = None
    pos_tag: str | None = None
    morphology: str | None = None


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


class ResolveQueryRequest(BaseModel):
    query_text: str = Field(..., min_length=1)
    include_translations: bool = True
    include_language_detection: bool = True


class WordActionSuggestion(BaseModel):
    action_type: Literal["open_wordbank", "add_as_new", "add_variation"]
    surface: str
    lemma: str
    translation_label: str | None = None
    direction: Literal["da_to_en", "en_to_da", "variation", "known"]
    direction_label: str | None = None
    pos_tag: str | None = None
    morphology: str | None = None
    show_lemma: bool = False


class ResolveQueryResponse(BaseModel):
    class MatchedLemmaSummary(BaseModel):
        lemma: str
        english_translation: str | None
        variation_count: int

    query_surface: str
    query_lemma: str | None
    classification: Literal["known", "variation", "typo_likely", "uncertain", "new"]
    matched_lemma: str | None
    matched_lemma_summary: MatchedLemmaSummary | None = None
    query_pos_tag: str | None
    query_morphology: str | None
    resolved_surface: str
    resolved_lemma: str | None
    da_to_en_translation: str | None
    en_to_da_translation: str | None
    en_to_da_lemma: str | None
    en_to_da_pos_tag: str | None
    en_to_da_morphology: str | None
    query_language: Literal["en", "da", "ambiguous"] | None
    query_language_confidence: float | None
    word_actions: list[WordActionSuggestion] = Field(default_factory=list)


class GeneratePhraseTranslationRequest(BaseModel):
    source_text: str = Field(..., min_length=1)


class GeneratePhraseTranslationResponse(BaseModel):
    status: Literal["generated", "cached", "unavailable"]
    source_text: str
    english_translation: str | None


class AddWordResponse(BaseModel):
    class VerificationResult(BaseModel):
        class SuggestedChanges(BaseModel):
            lemma_pos_tag: str | None = None
            lemma_morphology: str | None = None
            surface_pos_tag: str | None = None
            surface_morphology: str | None = None
            lexeme_translation: str | None = None
            surface_translation: str | None = None

        status: Literal["verified", "flagged", "error", "skipped", "queued"]
        provider: str | None = None
        reviewer_role: str | None = None
        message: str
        composed_word_count: int | None = None
        problem: str | None = None
        change_to_implement: str | None = None
        suggested_changes: SuggestedChanges | None = None

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


class GeneratePronunciationRequest(BaseModel):
    stored_lemma: str = Field(..., min_length=1)
    stored_surface_form: str | None = None
    force: bool = False


class GeneratePronunciationResponse(BaseModel):
    status: Literal["generated", "unavailable", "skipped"]
    stored_lemma: str
    stored_surface_form: str | None
    pronunciation_form: str | None


class ApplyVerificationChangesRequest(BaseModel):
    class SuggestedChanges(BaseModel):
        lemma_pos_tag: str | None = None
        lemma_morphology: str | None = None
        surface_pos_tag: str | None = None
        surface_morphology: str | None = None
        lexeme_translation: str | None = None
        surface_translation: str | None = None

    stored_lemma: str = Field(..., min_length=1)
    stored_surface_form: str | None = None
    suggested_changes: SuggestedChanges
    provider: str | None = None


class ApplyVerificationChangesResponse(BaseModel):
    status: Literal["applied", "skipped"]
    stored_lemma: str
    stored_surface_form: str | None
    applied_fields: list[str] = Field(default_factory=list)


class LemmaSummary(BaseModel):
    lemma: str
    display_lemma: str
    english_translation: str | None
    variation_count: int


class LemmaListResponse(BaseModel):
    items: list[LemmaSummary]


class WordbankSearchItem(BaseModel):
    lemma: str
    display_lemma: str
    english_translation: str | None
    variation_count: int
    match_surface: str | None = None


class WordbankSearchResponse(BaseModel):
    items: list[WordbankSearchItem]


class LemmaDetailsResponse(BaseModel):
    pos_tag: str | None = None
    morphology: str | None = None

    class SurfaceFormDetails(BaseModel):
        form: str
        english_translation: str | None
        pos_tag: str | None = None
        morphology: str | None = None
        has_pronunciation: bool = False

    lemma: str
    english_translation: str | None
    surface_forms: list[SurfaceFormDetails]


class ResetDatabaseResponse(BaseModel):
    status: Literal["reset"]
    message: str
