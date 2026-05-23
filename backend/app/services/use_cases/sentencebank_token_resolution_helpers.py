from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.db.repositories.sentencebank import SentenceTokenWriteRecord
from app.services.gemini_translation import NonCORWordGenerationInput, NonCORWordGenerationResult
from app.services.use_cases.sentencebank_candidates import SentenceMeaningCandidate
from app.services.use_cases.sentencebank_contextual_translations import is_existential_der_context
from app.services.use_cases.sentencebank_token_persistence import (
    persist_candidate_to_wordbank,
    persist_generated_to_wordbank,
    save_root_level_sentence_token,
    sentence_token_from_saved_word,
)

if TYPE_CHECKING:
    from app.services.use_cases.wordbank.runtime import WordbankRuntime


@dataclass(frozen=True, slots=True)
class PendingSentenceTokenSelection:
    token_index: int
    display_surface: str
    normalized_surface: str
    lemma_candidate: str
    pos_tag: str | None
    morphology: str | None
    sentence_context: str
    candidates: tuple[SentenceMeaningCandidate, ...]


@dataclass(frozen=True, slots=True)
class PendingGeneratedSentenceToken:
    token_index: int
    display_surface: str
    normalized_surface: str
    lemma_candidate: str
    pos_tag: str | None
    morphology: str | None
    sentence_context: str


def batch_select_sentence_candidates(
    runtime: WordbankRuntime,
    pending_selections: list[PendingSentenceTokenSelection],
) -> list[SentenceMeaningCandidate | None]:
    selected_ids = runtime.translation.select_meaning_sections_batch(
        [
            {
                "surface_form": selection.normalized_surface,
                "lemma": selection.lemma_candidate,
                "pos_tag": selection.pos_tag,
                "morphology": selection.morphology,
                "gloss": None,
                "english_translation": None,
                "sentence_context": selection.sentence_context,
                "meaning_candidates": list(selection.candidates),
            }
            for selection in pending_selections
        ]
    )
    resolved: list[SentenceMeaningCandidate | None] = []
    for selection, selected_id in zip(pending_selections, selected_ids, strict=False):
        resolved.append(
            next((candidate for candidate in selection.candidates if candidate.id == selected_id), None)
        )
    if len(resolved) < len(pending_selections):
        resolved.extend([None] * (len(pending_selections) - len(resolved)))
    return resolved


def finalize_pending_sentence_token(
    runtime: WordbankRuntime,
    *,
    wordbank_use_case,
    selection: PendingSentenceTokenSelection,
    selected_candidate: SentenceMeaningCandidate | None,
) -> tuple[SentenceTokenWriteRecord, bool] | None:
    if selected_candidate is None:
        return None
    persisted_response = persist_candidate_to_wordbank(
        wordbank_use_case,
        normalized_surface=selection.normalized_surface,
        candidate=selected_candidate,
    )
    if persisted_response is not None:
        persisted = sentence_token_from_saved_word(
            runtime,
            token_index=selection.token_index,
            display_surface=selection.display_surface,
            normalized_surface=selection.normalized_surface,
            stored_lemma=selected_candidate.lemma,
            meaning_id=(
                persisted_response.meaning.id if persisted_response.meaning is not None else None
            ),
        )
        if persisted is not None:
            return persisted, True

    return (
        save_root_level_sentence_token(
            runtime,
            token_index=selection.token_index,
            display_surface=selection.display_surface,
            normalized_surface=selection.normalized_surface,
            lemma=selected_candidate.lemma,
            pos_tag=selected_candidate.pos_tag or selection.pos_tag,
            morphology=selected_candidate.morphology or selection.morphology,
            cor_id=selected_candidate.cor_id,
            gloss=selected_candidate.gloss,
            english_translation=selected_candidate.english_translation,
            gloss_translation=selected_candidate.gloss_translation,
            queue_verification=False,
        ),
        True,
    )


def batch_generate_non_cor_sentence_tokens(
    runtime: WordbankRuntime,
    pending_generations: list[PendingGeneratedSentenceToken],
) -> list[NonCORWordGenerationResult | None]:
    return runtime.translation.generate_non_cor_word_entries_batch(
        [
            NonCORWordGenerationInput(
                surface_form=selection.normalized_surface,
                lemma_candidate=selection.lemma_candidate,
                pos_tag=selection.pos_tag,
                morphology=selection.morphology,
                sentence_context=selection.sentence_context,
            )
            for selection in pending_generations
        ]
    )


def should_generate_non_cor_sentence_token(pos_tag: str | None) -> bool:
    resolved = (pos_tag or "").upper()
    if not resolved:
        return True
    return resolved in {"ADJ", "NOUN", "PROPN"}


def should_use_static_pronoun_sentence_token(pos_tag: str | None) -> bool:
    return pos_tag is None or (pos_tag or "").upper() in {"ADV", "DET", "PRON"}


def _should_prefer_static_builtin(
    *,
    normalized_surface: str,
    pos_tag: str | None,
    sentence_context: str | None,
) -> bool:
    if normalized_surface == "der" and is_existential_der_context(sentence_context):
        return True
    if normalized_surface in {"en", "et"}:
        return True
    return (pos_tag or "").upper() in {"ADP", "ADV", "CCONJ", "DET", "NUM", "PRON"}


def finalize_generated_sentence_token(
    runtime: WordbankRuntime,
    *,
    wordbank_use_case,
    selection: PendingGeneratedSentenceToken,
    generated_candidate: NonCORWordGenerationResult | None,
) -> tuple[SentenceTokenWriteRecord, bool]:
    if generated_candidate is not None:
        persisted_response = persist_generated_to_wordbank(
            wordbank_use_case,
            normalized_surface=selection.normalized_surface,
            generated=generated_candidate,
        )
        if persisted_response is not None:
            persisted = sentence_token_from_saved_word(
                runtime,
                token_index=selection.token_index,
                display_surface=selection.display_surface,
                normalized_surface=selection.normalized_surface,
                stored_lemma=generated_candidate.lemma,
                meaning_id=(
                    persisted_response.meaning.id if persisted_response.meaning is not None else None
                ),
            )
            if persisted is not None:
                return persisted, True
        fallback_lemma = generated_candidate.lemma
        fallback_pos = generated_candidate.surface_pos_tag or generated_candidate.pos_tag or selection.pos_tag
        fallback_morphology = (
            generated_candidate.surface_morphology
            or generated_candidate.morphology
            or selection.morphology
        )
        fallback_gloss = generated_candidate.gloss
        fallback_translation = generated_candidate.english_translation
    else:
        fallback_lemma = selection.lemma_candidate
        fallback_pos = selection.pos_tag
        fallback_morphology = selection.morphology
        fallback_gloss = None
        fallback_translation = None

    return (
        save_root_level_sentence_token(
            runtime,
            token_index=selection.token_index,
            display_surface=selection.display_surface,
            normalized_surface=selection.normalized_surface,
            lemma=fallback_lemma,
            pos_tag=fallback_pos,
            morphology=fallback_morphology,
            cor_id=None,
            gloss=fallback_gloss,
            english_translation=fallback_translation,
            gloss_translation=None,
            queue_verification=False,
        ),
        True,
    )
