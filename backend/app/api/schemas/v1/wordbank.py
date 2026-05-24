from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_serializer


class AddWordRequest(BaseModel):
    class SearchSeed(BaseModel):
        lemma: str = Field(..., min_length=1)
        surface: str = Field(..., min_length=1)
        cor_id: str | None = None
        cor_lemma_idx: int | None = None
        dictionary_status: Literal["cor", "generated_non_cor", "unknown"] | None = None
        meaning_key: str | None = None
        gloss: str | None = None
        english_translation: str | None = None
        pos_tag: str | None = None
        morphology: str | None = None
        target_meaning_id: int | None = None

    surface_token: str = Field(..., min_length=1)
    lemma_candidate: str | None = None
    cor_id: str | None = None
    pos_tag: str | None = None
    morphology: str | None = None
    search_seed: SearchSeed | None = None


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
    cor_id: str | None = None
    translation_label: str | None = None
    direction: Literal["da_to_en", "en_to_da", "variation", "known"]
    direction_label: str | None = None
    pos_tag: str | None = None
    morphology: str | None = None
    show_lemma: bool = False
    meaning_key: str | None = None
    gloss: str | None = None
    english_translation: str | None = None
    alternative_translations: list[str] = Field(default_factory=list)
    cor_lemma_idx: int | None = None
    saved_meaning_id: int | None = None
    example_da: str | None = None
    example_en: str | None = None


class ENSenseOut(BaseModel):
    pos_ud: str
    sense_idx: int
    gloss: str
    danish_translation: str | None = None
    examples: list[str] = Field(default_factory=list)


class ENPosGroup(BaseModel):
    lemma: str
    form: str | None = None
    pos_ud: str
    pos_raw: str | None = None
    danish_translation: str | None = None
    meaning_description: str | None = None
    senses: list[ENSenseOut] = Field(default_factory=list)


class ENSearchFormResponse(BaseModel):
    form: str
    groups: list[ENPosGroup] = Field(default_factory=list)


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
    en_pos_groups: list[ENPosGroup] = Field(default_factory=list)


class ExpandLemmaSensesRequest(BaseModel):
    lemma: str = Field(..., min_length=1)


class ExpandLemmaSensesResponse(BaseModel):
    lemma: str
    status: Literal[
        "expanded",
        "already_expanded",
        "lemma_not_found",
        "pos_unsupported",
        "no_senses",
    ]
    discovered_count: int
    inserted_count: int
    renamed_legacy: bool


class GeneratePhraseTranslationRequest(BaseModel):
    source_text: str = Field(..., min_length=1)


class GeneratePhraseTranslationResponse(BaseModel):
    status: Literal["generated", "cached", "unavailable"]
    source_text: str
    english_translation: str | None


class QueuedBackgroundTask(BaseModel):
    status: Literal["queued", "skipped"]
    form: str | None = None


class MeaningContext(BaseModel):
    id: int
    meaning_key: str
    gloss: str | None = None
    english_translation: str | None = None


class VerificationAction(BaseModel):
    action_type: Literal["fix_translation", "fix_variations", "move_to_meaning_section", "move_to_lemma"]
    reason: str | None = None
    english_translation: str | None = None
    singular_indefinite_forms: list[str] | None = None
    singular_indefinite_n_word_forms: list[str] | None = None
    singular_indefinite_t_word_forms: list[str] | None = None
    singular_definite_forms: list[str] | None = None
    plural_indefinite_forms: list[str] | None = None
    plural_definite_forms: list[str] | None = None
    infinitive_forms: list[str] | None = None
    present_forms: list[str] | None = None
    past_forms: list[str] | None = None
    imperative_forms: list[str] | None = None
    past_participle_forms: list[str] | None = None
    target_meaning_id: int | None = None
    target_lemma: str | None = None
    target_meaning_key: str | None = None
    target_gloss: str | None = None
    target_english_translation: str | None = None
    target_pos_tag: str | None = None
    target_morphology: str | None = None


class VerificationResult(BaseModel):
    status: Literal["verified", "flagged", "error", "skipped", "queued"]
    provider: str | None = None
    reviewer_role: str | None = None
    review_intent: str | None = None
    message: str
    composed_word_count: int | None = None
    stored_surface_form: str | None = None
    requested_at: str | None = None
    completed_at: str | None = None
    problem: str | None = None
    change_to_implement: str | None = None
    suggested_actions: list[VerificationAction] = Field(default_factory=list)


class VerificationTargetRef(BaseModel):
    meaning_id: int | None = None
    stored_surface_form: str | None = None


class AddWordResponse(BaseModel):
    status: Literal["inserted", "exists"]
    stored_lemma: str
    stored_surface_form: str | None
    source: Literal["manual"]
    message: str
    meaning: MeaningContext | None = None
    verification: VerificationResult | None = None
    queued_verification_targets: list[VerificationTargetRef] = Field(default_factory=list)
    queued_pronunciation_forms: list[str] = Field(default_factory=list)
    pronunciation: QueuedBackgroundTask | None = None
    saved_snapshot: LemmaDetailsResponse | None = None


class VerifyWordRequest(BaseModel):
    stored_lemma: str = Field(..., min_length=1)
    stored_surface_form: str | None = None
    meaning_id: int | None = None


class VerifyWordResponse(BaseModel):
    stored_lemma: str
    stored_surface_form: str | None
    verification: VerificationResult
    applied_categories: list[str] = Field(default_factory=list)


class QueueVerificationRequest(BaseModel):
    stored_lemma: str = Field(..., min_length=1)
    stored_surface_form: str | None = None
    meaning_id: int | None = None
    review_intent: str | None = None


class QueueVerificationResponse(BaseModel):
    stored_lemma: str
    stored_surface_form: str | None
    meaning_id: int | None = None
    review_intent: str
    verification: VerificationResult


class RethinkCategoriesRequest(BaseModel):
    stored_lemma: str = Field(..., min_length=1)
    stored_surface_form: str | None = None
    meaning_id: int | None = None


class RethinkCategoriesResponse(BaseModel):
    status: Literal["updated", "skipped", "error"]
    stored_lemma: str
    stored_surface_form: str | None
    meaning_id: int | None = None
    applied_categories: list[str] = Field(default_factory=list)
    message: str


class FindAlternativeTranslationsRequest(BaseModel):
    stored_lemma: str = Field(..., min_length=1)
    meaning_id: int | None = None


class FindAlternativeTranslationsResponse(BaseModel):
    status: Literal["updated", "skipped", "error"]
    stored_lemma: str
    meaning_id: int | None = None
    primary_translation: str | None = None
    added_additional_translations: list[str] = Field(default_factory=list)
    message: str


class CompleteVariationsRequest(BaseModel):
    stored_lemma: str = Field(..., min_length=1)
    meaning_id: int = Field(..., ge=1)


class CompleteVariationsResponse(BaseModel):
    status: Literal["updated", "skipped"]
    stored_lemma: str
    meaning_id: int
    added_surface_forms: list[str] = Field(default_factory=list)
    queued_pronunciation_forms: list[str] = Field(default_factory=list)
    queued_verification_targets: list[VerificationTargetRef] = Field(default_factory=list)
    message: str


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
    stored_lemma: str = Field(..., min_length=1)
    stored_surface_form: str | None = None
    meaning_id: int | None = None
    action: VerificationAction
    provider: str | None = None


class ApplyVerificationChangesResponse(BaseModel):
    status: Literal["applied", "skipped"]
    stored_lemma: str
    stored_surface_form: str | None
    applied_action_type: str | None = None
    target_lemma: str | None = None
    target_meaning_id: int | None = None


class VerificationChangeEntry(BaseModel):
    id: int
    stored_lemma: str
    stored_surface_form: str | None
    meaning_id: int | None
    action_type: str
    before_json: dict[str, object]
    after_json: dict[str, object]
    applied_at: str
    reverted_at: str | None
    provider: str | None


class GetVerificationChangesResponse(BaseModel):
    items: list[VerificationChangeEntry]


class RevertVerificationChangeRequest(BaseModel):
    change_id: int
    stored_lemma: str = Field(..., min_length=1)


class RevertVerificationChangeResponse(BaseModel):
    status: Literal["reverted", "already_reverted", "not_found"]
    change_id: int


class LemmaSummary(BaseModel):
    lemma: str
    display_lemma: str
    english_translation: str | None
    pos_tags: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    variation_count: int


class LemmaListResponse(BaseModel):
    items: list[LemmaSummary]


class WordbankSearchItem(BaseModel):
    lemma: str
    display_lemma: str
    meaning_id: int | None = None
    meaning_key: str | None = None
    gloss: str | None = None
    gloss_translation: str | None = None
    cor_lemma_idx: int | None = None
    english_translation: str | None
    variation_count: int
    match_surface: str | None = None
    query_cor_ids: list[str] = Field(default_factory=list)
    pos_tag: str | None = None
    morphology: str | None = None


class WordbankSearchResponse(BaseModel):
    items: list[WordbankSearchItem]
    did_you_mean: str | None = None


class CORSearchVariant(BaseModel):
    cor_id: str
    form: str
    lemma: str
    dictionary_status: Literal["cor", "generated_non_cor", "unknown"] = "cor"
    gloss: str | None = None
    gloss_translation: str | None = None
    gram_raw: str
    norm: str | None = None
    lemma_idx: int
    gram_code: int
    variation: int
    pos_tag: str | None = None
    morphology: str | None = None
    features: dict[str, str] = Field(default_factory=dict)
    extra_tags: list[str] = Field(default_factory=list)
    lemma_translation: str | None = None
    saveable_translation: str | None = None
    lemma_translation_provider: str | None = None
    lemma_translation_status: Literal["provider", "gemini", "gloss_fallback", "missing"] | None = None
    lemma_translation_reason: str | None = None
    meaning_key: str | None = None
    alternative_translations: list[str] = Field(default_factory=list)
    saved_meaning_id: int | None = None
    example_da: str | None = None
    example_en: str | None = None


class CORSearchGroup(BaseModel):
    lemma: str
    gloss: str | None = None
    pos_tag: str | None = None
    variants: list[CORSearchVariant] = Field(default_factory=list)


class CORSearchFormResponse(BaseModel):
    form: str
    groups: list[CORSearchGroup] = Field(default_factory=list)
    did_you_mean: str | None = None


class CORSearchFormBatchRequest(BaseModel):
    class Item(BaseModel):
        form: str = Field(..., min_length=1)
        en_query: str | None = Field(default=None, min_length=1)
        en_pos_ud: str | None = Field(default=None, min_length=1)

    items: list[Item] = Field(default_factory=list, max_length=25)
    limit: int = Field(default=100, ge=1, le=500)
    include_translations: bool = False


class CORSearchFormBatchResponse(BaseModel):
    items: list[CORSearchFormResponse] = Field(default_factory=list)


class CORLemmaParadigmResponse(BaseModel):
    lemma_idx: int
    variants: list[CORSearchVariant] = Field(default_factory=list)


class LemmaDetailsResponse(BaseModel):
    dictionary_status: Literal["cor", "generated_non_cor", "unknown"] = "unknown"
    pos_tag: str | None = None
    morphology: str | None = None

    class ReferenceLink(BaseModel):
        page_id: str
        page_title: str
        tab_id: str
        tab_title: str
        sentinel: str

    class SurfaceFormDetails(BaseModel):
        form: str
        pos_tag: str | None = None
        morphology: str | None = None
        lemma: str | None = None
        lemma_translation: str | None = None
        gloss: str | None = None
        gloss_translation: str | None = None
        gram_raw: str | None = None
        has_pronunciation: bool = False
        verification: VerificationResult | None = None

        @model_serializer(mode="wrap")
        def _serialize_without_empty_fields(self, handler):
            data = handler(self)
            gram_raw = data.get("gram_raw")
            if isinstance(gram_raw, str) and gram_raw.strip():
                parts = [part.strip() for part in gram_raw.split(".") if part.strip()]
                data["gram_raw"] = ". ".join(parts) if parts else gram_raw
            return {key: value for key, value in data.items() if value is not None}

    class MeaningSection(BaseModel):
        id: int
        meaning_key: str
        dictionary_status: Literal["cor", "generated_non_cor", "unknown"] = "unknown"
        gloss: str | None = None
        english_translation: str | None = None
        additional_translations: list[str] = Field(default_factory=list)
        gloss_translation: str | None = None
        pos_tag: str | None = None
        morphology: str | None = None
        gram_raw: str | None = None
        categories: list[str] = Field(default_factory=list)
        reference_links: list[LemmaDetailsResponse.ReferenceLink] = Field(default_factory=list)
        verification: VerificationResult | None = None
        surface_forms: list[LemmaDetailsResponse.SurfaceFormDetails] = Field(default_factory=list)

        @model_serializer(mode="wrap")
        def _serialize_without_empty_fields(self, handler):
            data = handler(self)
            gram_raw = data.get("gram_raw")
            if isinstance(gram_raw, str) and gram_raw.strip():
                parts = [part.strip() for part in gram_raw.split(".") if part.strip()]
                data["gram_raw"] = ". ".join(parts) if parts else gram_raw
            return {key: value for key, value in data.items() if value is not None}

    class RelatedWordSavedMatch(BaseModel):
        status: Literal["unsaved", "saved_lemma", "saved_variation"]
        target_lemma: str | None = None
        target_meaning_id: int | None = None

        @model_serializer(mode="wrap")
        def _serialize_without_empty_fields(self, handler):
            data = handler(self)
            return {key: value for key, value in data.items() if value is not None}

    class RelatedWord(BaseModel):
        id: int
        relation_type: Literal["compound_component", "compound_host"]
        lemma: str
        english_translation: str | None = None
        pos_tag: str | None = None
        saved_match: LemmaDetailsResponse.RelatedWordSavedMatch
        display_variant: CORSearchVariant | None = None
        candidate_variants: list[CORSearchVariant] = Field(default_factory=list)

        @model_serializer(mode="wrap")
        def _serialize_without_empty_fields(self, handler):
            data = handler(self)
            return {key: value for key, value in data.items() if value is not None}

    class RelatedWordsSection(BaseModel):
        status: Literal["queued", "ready", "empty", "error"]
        message: str | None = None
        items: list[LemmaDetailsResponse.RelatedWord] = Field(default_factory=list)

        @model_serializer(mode="wrap")
        def _serialize_without_empty_fields(self, handler):
            data = handler(self)
            return {key: value for key, value in data.items() if value is not None}

    class LinkedSentence(BaseModel):
        id: int
        source_text: str
        english_translation: str | None = None
        created_at: str
        matched_token_indexes: list[int] = Field(default_factory=list)
        tokens: list[SentenceTokenCard] = Field(default_factory=list)

        @model_serializer(mode="wrap")
        def _serialize_without_empty_fields(self, handler):
            data = handler(self)
            return {key: value for key, value in data.items() if value is not None}

    lemma: str
    english_translation: str | None
    additional_translations: list[str] = Field(default_factory=list)
    is_sectioned: bool = False
    categories: list[str] = Field(default_factory=list)
    reference_links: list[ReferenceLink] = Field(default_factory=list)
    verification: VerificationResult | None = None
    meaning_sections: list[MeaningSection] = Field(default_factory=list)
    surface_forms: list[SurfaceFormDetails]
    related_words: RelatedWordsSection = Field(
        default_factory=lambda: LemmaDetailsResponse.RelatedWordsSection(status="empty", items=[])
    )
    linked_sentences: list[LinkedSentence] = Field(default_factory=list)


class ResetDatabaseResponse(BaseModel):
    status: Literal["reset"]
    message: str


class SeedNumbersAudioResponse(BaseModel):
    generated: int
    skipped: int
    failed: int
    message: str


class SeedPresavedWordsAudioResponse(BaseModel):
    generated: int
    skipped: int
    failed: int
    message: str


class DeleteMeaningResponse(BaseModel):
    was_lemma_deleted: bool
    message: str


class DeleteLemmaResponse(BaseModel):
    status: Literal["deleted"] = "deleted"
    message: str


from app.api.schemas.v1.sentencebank import SentenceTokenCard

AddWordResponse.model_rebuild()
LemmaDetailsResponse.model_rebuild()
