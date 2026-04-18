from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol


class VerificationError(RuntimeError):
    """Raised when verification cannot be completed by the provider."""


@dataclass(frozen=True)
class WordVerificationMeaningSection:
    id: int
    meaning_key: str
    gloss: str | None
    gloss_translation: str | None
    english_translation: str | None
    pos_tag: str | None
    morphology: str | None
    surface_forms: tuple[str, ...]


@dataclass(frozen=True)
class WordVerificationSurfaceForm:
    form: str
    meaning_id: int | None
    meaning_key: str | None
    gloss: str | None
    gloss_translation: str | None
    english_translation: str | None
    pos_tag: str | None
    morphology: str | None
    source: str | None
    gram_raw: str | None = None


@dataclass(frozen=True)
class WordVerificationInput:
    stored_lemma: str
    stored_surface_form: str | None
    meaning_id: int | None
    meaning_key: str | None
    meaning_gloss: str | None
    meaning_gloss_translation: str | None
    lexeme_source: str
    selected_translation: str | None
    selected_translation_scope: Literal["lemma", "meaning_section"] | None
    surface_source: str | None
    canonical_lemma: str | None
    canonical_lemma_pos_tag: str | None
    canonical_lemma_morphology: str | None
    selected_meaning_pos_tag: str | None
    selected_meaning_morphology: str | None
    selected_surface_pos_tag: str | None
    selected_surface_morphology: str | None
    current_categories: tuple[str, ...] = ()
    available_categories: tuple[str, ...] = ()
    sibling_meaning_sections: tuple[WordVerificationMeaningSection, ...] = ()
    available_surface_forms: tuple[WordVerificationSurfaceForm, ...] = ()
    review_intent: Literal["general", "complete_variations"] = "general"


@dataclass(frozen=True)
class WordVerificationAction:
    action_type: Literal["fix_translation", "fix_variations", "move_to_meaning_section", "move_to_lemma"]
    reason: str | None = None
    english_translation: str | None = None
    singular_indefinite_forms: tuple[str, ...] = ()
    singular_indefinite_n_word_forms: tuple[str, ...] = ()
    singular_indefinite_t_word_forms: tuple[str, ...] = ()
    singular_definite_forms: tuple[str, ...] = ()
    plural_indefinite_forms: tuple[str, ...] = ()
    plural_definite_forms: tuple[str, ...] = ()
    infinitive_forms: tuple[str, ...] = ()
    present_forms: tuple[str, ...] = ()
    past_forms: tuple[str, ...] = ()
    imperative_forms: tuple[str, ...] = ()
    past_participle_forms: tuple[str, ...] = ()
    target_meaning_id: int | None = None
    target_lemma: str | None = None
    target_meaning_key: str | None = None
    target_gloss: str | None = None
    target_english_translation: str | None = None
    target_pos_tag: str | None = None
    target_morphology: str | None = None


@dataclass(frozen=True)
class WordVerificationResult:
    verdict: Literal["verified", "flagged"]
    message: str
    composed_word_count: int | None = None
    problem: str | None = None
    change_to_implement: str | None = None
    suggested_actions: tuple[WordVerificationAction, ...] = ()


@dataclass(frozen=True)
class WordCategoryClassificationResult:
    categories: tuple[str, ...] = ()


class WordVerificationService(Protocol):
    provider: str
    reviewer_role: str

    def verify_word_entry(self, payload: WordVerificationInput) -> WordVerificationResult: ...
    def classify_word_categories(self, payload: WordVerificationInput) -> WordCategoryClassificationResult: ...
    def verify_word_entries_batch(
        self,
        payloads: list[WordVerificationInput],
        sentence_context: str | None = None,
    ) -> list[WordVerificationResult]: ...
