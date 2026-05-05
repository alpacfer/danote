from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


class GeminiTranslationError(RuntimeError):
    """Raised when Gemini word translation cannot be completed."""


@dataclass(frozen=True, slots=True)
class ContextualWordTranslationInput:
    surface_form: str
    lemma: str
    pos_tag: str | None = None
    morphology: str | None = None
    gloss: str | None = None
    lemma_translation_hint: str | None = None
    gloss_translation_hint: str | None = None


@dataclass(frozen=True, slots=True)
class MeaningSectionCandidateInput:
    id: int
    lemma: str
    meaning_key: str
    cor_lemma_idx: int | None = None
    gloss: str | None = None
    english_translation: str | None = None
    pos_tag: str | None = None
    morphology: str | None = None


@dataclass(frozen=True, slots=True)
class MeaningSectionSelectionInput:
    surface_form: str
    lemma: str
    pos_tag: str | None = None
    morphology: str | None = None
    gloss: str | None = None
    english_translation: str | None = None
    sentence_context: str | None = None
    meaning_candidates: list[MeaningSectionCandidateInput] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class AlternativeTranslationsInput:
    surface_form: str
    lemma: str
    pos_tag: str | None = None
    morphology: str | None = None
    gloss: str | None = None
    current_translation: str | None = None
    existing_additional_translations: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class AlternativeTranslationsResult:
    primary_translation: str | None = None
    alternative_translations: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ExampleSentenceGenerationInput:
    stored_lemma: str
    meaning_id: int
    meaning_key: str
    gloss: str | None = None
    gloss_translation: str | None = None
    english_translation: str | None = None
    additional_translations: list[str] = field(default_factory=list)
    pos_tag: str | None = None
    morphology: str | None = None
    cor_lemma_idx: int | None = None
    surface_forms: list[str] = field(default_factory=list)
    tense_label: str | None = None
    existing_examples: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ExampleSentenceGenerationResult:
    source_text: str
    english_translation: str


@dataclass(frozen=True, slots=True)
class NonCORWordGenerationInput:
    surface_form: str
    lemma_candidate: str
    pos_tag: str | None = None
    morphology: str | None = None
    sentence_context: str | None = None


@dataclass(frozen=True, slots=True)
class NonCORWordGenerationResult:
    lemma: str
    english_translation: str | None = None
    meaning_key: str | None = None
    gloss: str | None = None
    pos_tag: str | None = None
    morphology: str | None = None
    surface_pos_tag: str | None = None
    surface_morphology: str | None = None


@dataclass(frozen=True, slots=True)
class NonCORVariationCandidate:
    form: str
    pos_tag: str | None = None
    morphology: str | None = None


@dataclass(frozen=True, slots=True)
class NonCORVariationGenerationInput:
    stored_lemma: str
    english_translation: str | None = None
    meaning_key: str | None = None
    gloss: str | None = None
    pos_tag: str | None = None
    morphology: str | None = None
    existing_forms: list[NonCORVariationCandidate] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class NonCORVariationGenerationResult:
    forms: list[NonCORVariationCandidate] = field(default_factory=list)


class GeminiWordTranslationService(Protocol):
    provider: str

    def translate_word(self, payload: ContextualWordTranslationInput) -> str | None: ...
    def translate_words_batch(
        self, payloads: list[ContextualWordTranslationInput]
    ) -> list[str | None]: ...
    def select_meaning_section(self, payload: MeaningSectionSelectionInput) -> int | None: ...
    def select_meaning_sections_batch(
        self, payloads: list[MeaningSectionSelectionInput]
    ) -> list[int | None]: ...
    def find_alternative_translations(
        self, payload: AlternativeTranslationsInput
    ) -> AlternativeTranslationsResult: ...
    def generate_example_sentence(
        self, payload: ExampleSentenceGenerationInput
    ) -> ExampleSentenceGenerationResult | None: ...
    def generate_non_cor_word_entry(
        self, payload: NonCORWordGenerationInput
    ) -> NonCORWordGenerationResult | None: ...
    def generate_non_cor_word_entries_batch(
        self, payloads: list[NonCORWordGenerationInput]
    ) -> list[NonCORWordGenerationResult | None]: ...
    def complete_non_cor_meaning_variations(
        self, payload: NonCORVariationGenerationInput
    ) -> NonCORVariationGenerationResult: ...
