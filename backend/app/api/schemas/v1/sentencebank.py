from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.api.schemas.v1.wordbank import CORSearchVariant


class AddSentenceRequest(BaseModel):
    source_text: str = Field(..., min_length=1)
    english_translation: str | None = None
    token_persistence_mode: Literal["auto_save_all", "link_existing_only"] = "auto_save_all"
    target: SentenceTargetRequest | None = None


class SentenceTargetRequest(BaseModel):
    stored_lemma: str = Field(..., min_length=1)
    meaning_id: int = Field(..., ge=1)


class SentenceTokenCard(BaseModel):
    token_index: int
    surface_form: str
    save_status: Literal["saved", "unsaved"] = "saved"
    lemma_candidate: str | None = None
    stored_lemma: str | None = None
    lexeme_id: int | None = None
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
    has_pronunciation: bool = False
    tokens: list[SentenceTokenCard] = Field(default_factory=list)


class QueuedSentencePronunciationTask(BaseModel):
    status: Literal["queued", "skipped"]
    sentence_id: int


class QueuedSentenceVerificationTarget(BaseModel):
    stored_lemma: str
    meaning_id: int | None = None
    stored_surface_form: str | None = None


class AddSentenceResponse(SentenceSummary):
    status: Literal["inserted", "exists"]
    message: str
    pronunciation: QueuedSentencePronunciationTask | None = None
    queued_verification_targets: list[QueuedSentenceVerificationTarget] = Field(default_factory=list)


class SentenceListResponse(BaseModel):
    items: list[SentenceSummary]


class SaveSentenceTokenResponse(SentenceSummary):
    saved_token: SentenceTokenCard
    message: str
    queued_verification_targets: list[QueuedSentenceVerificationTarget] = Field(default_factory=list)


class GenerateExamplePreviewRequest(BaseModel):
    stored_lemma: str = Field(..., min_length=1)
    meaning_id: int = Field(..., ge=1)
    tense_label: str | None = None


class GenerateStaticExamplePreviewRequest(BaseModel):
    stored_lemma: str = Field(..., min_length=1)


class GenerateExamplePreviewResponse(BaseModel):
    source_text: str
    english_translation: str


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
    language_mode: Literal["da", "en"] | None = None


class SentenceSearchPreviewResponse(BaseModel):
    status: Literal["ready", "blocked", "preview"]
    query_language: Literal["da", "en", "unknown"] = "unknown"
    source_text: str | None = None
    english_translation: str | None = None
    is_valid: bool
    errors: list[SentenceVerificationErrorItem] = Field(default_factory=list)
    corrected_text: str | None = None
    message: str | None = None
    is_multi_word_expression: bool = False
    mwe_lemma: str | None = None
    mwe_pos_tag: str | None = None
    mwe_gloss: str | None = None
    mwe_english_translation: str | None = None
    # Single best-match for back-compat. When the lemma is polysemous (e.g.
    # "tage på"), this is the first / most common meaning; the frontend should
    # prefer `mwe_meanings` and fall back to this only if the list is empty.
    mwe_cor_match: CORSearchVariant | None = None
    # Distinct senses of the MWE lemma. Monosemous MWEs return a one-element
    # list (mirroring `mwe_cor_match`); polysemous MWEs return one entry per
    # sense. The frontend renders one search card per entry; saving each card
    # creates a separate `lexeme_meanings` row under the same MWE lexeme.
    mwe_meanings: list[CORSearchVariant] = Field(default_factory=list)


class GenerateSentencePronunciationRequest(BaseModel):
    sentence_id: int = Field(..., ge=1)
    force: bool = False


class GenerateSentencePronunciationResponse(BaseModel):
    status: Literal["generated", "unavailable", "skipped"]
    sentence_id: int
    source_text: str


class DeleteSentenceResponse(BaseModel):
    status: Literal["deleted"] = "deleted"
    message: str
