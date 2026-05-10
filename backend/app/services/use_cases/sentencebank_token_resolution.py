from __future__ import annotations

import re
from dataclasses import dataclass

from app.db.repositories.sentencebank import SentenceTokenWriteRecord
from app.nlp.adapter import NLPToken
from app.nlp.token_filter import is_wordlike_token
from app.services.concurrency import run_in_parallel
from app.services.gemini_translation import NonCORWordGenerationInput, NonCORWordGenerationResult
from app.services.token_classifier import normalize_token
from app.services.use_cases.sentencebank_candidates import (
    SentenceMeaningCandidate,
    select_sentence_candidate,
)
from app.services.use_cases.sentencebank_text import should_skip_sentence_wordbank_token
from app.services.use_cases.sentencebank_token_persistence import (
    existing_saved_token,
    persist_candidate_to_wordbank,
    persist_generated_to_wordbank,
    save_root_level_sentence_token,
    save_static_hv_word_sentence_token,
    save_static_pronoun_sentence_token,
    sentence_token_from_saved_word,
    unsaved_sentence_token,
    verification_metadata_for_new_sentence_token,
)
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


def resolve_sentence_tokens(
    runtime: WordbankRuntime | None,
    *,
    source_text: str,
    nlp_adapter,
    wordbank_use_case,
) -> tuple[list[SentenceTokenWriteRecord], list[dict[str, object]]]:
    if runtime is None or wordbank_use_case is None:
        return [], []

    sentence_tokens = (
        nlp_adapter.tokenize(source_text)
        if nlp_adapter is not None
        else fallback_sentence_tokens(source_text)
    )
    pending_selection_results: dict[int, SentenceMeaningCandidate | None] = {}
    pending_selections: list[PendingSentenceTokenSelection] = []
    pending_generation_results: dict[int, NonCORWordGenerationResult | None] = {}
    pending_generations: list[PendingGeneratedSentenceToken] = []
    planned_tokens: list[
        tuple[SentenceTokenWriteRecord, bool] | PendingSentenceTokenSelection | PendingGeneratedSentenceToken
    ] = []
    new_tokens: list[dict[str, object]] = []
    for nlp_token in sentence_tokens:
        surface_form = nlp_token.text.strip()
        if not surface_form or nlp_token.is_punctuation:
            continue
        if not is_wordlike_token(surface_form):
            continue
        raw_lemma_candidate = (nlp_token.lemma or "").strip()
        if should_skip_sentence_wordbank_token(
            surface_form=surface_form,
            lemma_candidate=raw_lemma_candidate or surface_form,
            pos_tag=nlp_token.pos,
            token_index=len(planned_tokens),
        ):
            continue
        normalized_surface = normalize_token(surface_form)
        if not normalized_surface:
            continue
        lemma_candidate = normalize_token(raw_lemma_candidate) or normalized_surface
        resolved_token = resolve_sentence_token(
            runtime,
            wordbank_use_case=wordbank_use_case,
            token_index=len(planned_tokens),
            display_surface=surface_form,
            normalized_surface=normalized_surface,
            lemma_candidate=lemma_candidate,
            pos_tag=nlp_token.pos,
            morphology=nlp_token.morphology,
            sentence_context=source_text,
        )
        if resolved_token is None:
            continue
        if isinstance(resolved_token, PendingSentenceTokenSelection):
            pending_selections.append(resolved_token)
            planned_tokens.append(resolved_token)
            continue
        if isinstance(resolved_token, PendingGeneratedSentenceToken):
            pending_generations.append(resolved_token)
            planned_tokens.append(resolved_token)
            continue
        planned_tokens.append(resolved_token)

    if pending_selections and pending_generations:
        selected_candidates, generated_candidates = run_in_parallel(
            lambda: batch_select_sentence_candidates(runtime, pending_selections),
            lambda: batch_generate_non_cor_sentence_tokens(runtime, pending_generations),
        )
        for selection, selected_candidate in zip(pending_selections, selected_candidates, strict=False):
            pending_selection_results[selection.token_index] = selected_candidate
        for selection, generated_candidate in zip(pending_generations, generated_candidates, strict=False):
            pending_generation_results[selection.token_index] = generated_candidate
    elif pending_selections:
        selected_candidates = batch_select_sentence_candidates(runtime, pending_selections)
        for selection, selected_candidate in zip(pending_selections, selected_candidates, strict=False):
            pending_selection_results[selection.token_index] = selected_candidate
    elif pending_generations:
        generated_candidates = batch_generate_non_cor_sentence_tokens(runtime, pending_generations)
        for selection, generated_candidate in zip(pending_generations, generated_candidates, strict=False):
            pending_generation_results[selection.token_index] = generated_candidate

    resolved: list[SentenceTokenWriteRecord] = []
    seen_verification_targets: set[tuple[str, str | None, int | None]] = set()
    for planned_token in planned_tokens:
        if isinstance(planned_token, PendingSentenceTokenSelection):
            selected_candidate = pending_selection_results.get(planned_token.token_index)
            resolved_token = finalize_pending_sentence_token(
                runtime,
                wordbank_use_case=wordbank_use_case,
                selection=planned_token,
                selected_candidate=selected_candidate,
            )
            if resolved_token is None:
                continue
            token, is_new = resolved_token
        elif isinstance(planned_token, PendingGeneratedSentenceToken):
            generated_candidate = pending_generation_results.get(planned_token.token_index)
            token, is_new = finalize_generated_sentence_token(
                runtime,
                wordbank_use_case=wordbank_use_case,
                selection=planned_token,
                generated_candidate=generated_candidate,
            )
        else:
            token, is_new = planned_token
        resolved.append(token)
        if is_new:
            for metadata in verification_metadata_for_new_sentence_token(token):
                key = (
                    str(metadata["stored_lemma"]),
                    (
                        str(metadata["stored_surface_form"])
                        if metadata["stored_surface_form"] is not None
                        else None
                    ),
                    int(metadata["meaning_id"]) if isinstance(metadata["meaning_id"], int) else None,
                )
                if key in seen_verification_targets:
                    continue
                seen_verification_targets.add(key)
                new_tokens.append(metadata)
    return resolved, new_tokens


def resolve_sentence_tokens_link_existing_only(
    runtime: WordbankRuntime | None,
    *,
    source_text: str,
    nlp_adapter,
    stored_lemma: str,
    meaning_id: int,
) -> list[SentenceTokenWriteRecord]:
    if runtime is None:
        return []
    normalized_target_lemma = normalize_token(stored_lemma)
    target_lexeme = runtime.repository.get_lexeme(normalized_target_lemma)
    target_meaning = runtime.repository.get_lexeme_meaning(meaning_id)
    target_meaning_ids = {
        meaning.id for meaning in runtime.repository.list_lexeme_meanings(target_lexeme.id)
    } if target_lexeme is not None else set()
    if target_lexeme is None or target_meaning is None or target_meaning.id not in target_meaning_ids:
        raise ValueError("target word meaning was not found")

    target_forms = {
        normalized_target_lemma,
        *(
            normalize_token(form.form)
            for form in runtime.repository.list_surface_forms(target_lexeme.id)
            if form.meaning_id in {None, meaning_id}
        ),
    }
    target_forms.discard("")
    sentence_tokens = (
        nlp_adapter.tokenize(source_text)
        if nlp_adapter is not None
        else fallback_sentence_tokens(source_text)
    )
    resolved: list[SentenceTokenWriteRecord] = []
    linked_target = False
    for nlp_token in sentence_tokens:
        surface_form = nlp_token.text.strip()
        if not surface_form or nlp_token.is_punctuation or not is_wordlike_token(surface_form):
            continue
        normalized_surface = normalize_token(surface_form)
        if not normalized_surface:
            continue
        token_index = len(resolved)
        if not linked_target and normalized_surface in target_forms:
            saved = sentence_token_from_saved_word(
                runtime,
                token_index=token_index,
                display_surface=surface_form,
                normalized_surface=normalized_surface,
                stored_lemma=normalized_target_lemma,
                meaning_id=meaning_id,
            )
            if saved is not None:
                resolved.append(saved)
                linked_target = True
                continue
        lemma_candidate = normalize_token((nlp_token.lemma or "").strip()) or normalized_surface
        resolved.append(
            unsaved_sentence_token(
                token_index=token_index,
                display_surface=surface_form,
                normalized_surface=normalized_surface,
                lemma_candidate=lemma_candidate,
                pos_tag=nlp_token.pos,
                morphology=nlp_token.morphology,
            )
        )
    if not linked_target:
        raise ValueError("generated example must include the target word")
    return resolved


def resolve_unsaved_sentence_token(
    runtime: WordbankRuntime | None,
    *,
    source_text: str,
    token,
    wordbank_use_case,
) -> tuple[SentenceTokenWriteRecord, list[dict[str, object]]]:
    if runtime is None or wordbank_use_case is None:
        raise RuntimeError("wordbank runtime is unavailable")
    normalized_surface = normalize_token(str(getattr(token, "normalized_surface", "") or ""))
    if not normalized_surface:
        normalized_surface = normalize_token(str(getattr(token, "surface_form", "") or ""))
    lemma_candidate = normalize_token(str(getattr(token, "lemma_candidate", "") or "")) or normalized_surface
    if not normalized_surface or not lemma_candidate:
        raise ValueError("sentence token is invalid")

    resolved_token = resolve_sentence_token(
        runtime,
        wordbank_use_case=wordbank_use_case,
        token_index=int(token.token_index),
        display_surface=str(token.surface_form),
        normalized_surface=normalized_surface,
        lemma_candidate=lemma_candidate,
        pos_tag=getattr(token, "pos_tag", None),
        morphology=getattr(token, "morphology", None),
        sentence_context=source_text,
        prefer_existing=False,
    )
    finalized = finalize_single_sentence_token(
        runtime,
        wordbank_use_case=wordbank_use_case,
        resolved_token=resolved_token,
    )
    if finalized is None:
        raise RuntimeError("Could not save sentence token.")
    saved_token, is_new = finalized
    return saved_token, verification_metadata_for_new_sentence_token(saved_token) if is_new else []


def finalize_single_sentence_token(
    runtime: WordbankRuntime,
    *,
    wordbank_use_case,
    resolved_token: tuple[SentenceTokenWriteRecord, bool] | PendingSentenceTokenSelection | PendingGeneratedSentenceToken | None,
) -> tuple[SentenceTokenWriteRecord, bool] | None:
    if resolved_token is None:
        return None
    if isinstance(resolved_token, PendingSentenceTokenSelection):
        selected = batch_select_sentence_candidates(runtime, [resolved_token])[0]
        return finalize_pending_sentence_token(
            runtime,
            wordbank_use_case=wordbank_use_case,
            selection=resolved_token,
            selected_candidate=selected,
        )
    if isinstance(resolved_token, PendingGeneratedSentenceToken):
        generated = batch_generate_non_cor_sentence_tokens(runtime, [resolved_token])[0]
        return finalize_generated_sentence_token(
            runtime,
            wordbank_use_case=wordbank_use_case,
            selection=resolved_token,
            generated_candidate=generated,
        )
    return resolved_token


def fallback_sentence_tokens(source_text: str) -> list[NLPToken]:
    return [
        NLPToken(text=match.group(0), lemma=match.group(0), pos=None, morphology=None, is_punctuation=False)
        for match in re.finditer(r"[\wÆØÅæøå]+(?:['’.-][\wÆØÅæøå]+)*", source_text)
    ]


def resolve_sentence_token(
    runtime: WordbankRuntime,
    *,
    wordbank_use_case,
    token_index: int,
    display_surface: str,
    normalized_surface: str,
    lemma_candidate: str,
    pos_tag: str | None,
    morphology: str | None,
    sentence_context: str,
    prefer_existing: bool = True,
) -> tuple[SentenceTokenWriteRecord, bool] | PendingSentenceTokenSelection | PendingGeneratedSentenceToken | None:
    if prefer_existing:
        existing = existing_saved_token(
            runtime,
            display_surface=display_surface,
            normalized_surface=normalized_surface,
            lemma_candidate=lemma_candidate,
            token_index=token_index,
            pos_tag=pos_tag,
            morphology=morphology,
            sentence_context=sentence_context,
        )
        if existing is not None:
            return existing, False

    if should_use_static_pronoun_sentence_token(pos_tag):
        static_hv_word = save_static_hv_word_sentence_token(
            runtime,
            token_index=token_index,
            display_surface=display_surface,
            normalized_surface=normalized_surface,
        )
        if static_hv_word is not None:
            return static_hv_word

        static_pronoun = save_static_pronoun_sentence_token(
            runtime,
            token_index=token_index,
            display_surface=display_surface,
            normalized_surface=normalized_surface,
            pos_tag=pos_tag,
            morphology=morphology,
            sentence_context=sentence_context,
        )
        if static_pronoun is not None:
            return static_pronoun

    candidate_resolution = select_sentence_candidate(
        runtime,
        surface_form=normalized_surface,
        lemma_candidate=lemma_candidate,
        pos_tag=pos_tag,
        morphology=morphology,
        sentence_context=sentence_context,
    )
    selected_candidate = candidate_resolution.candidate
    if selected_candidate is None:
        if candidate_resolution.is_ambiguous:
            return PendingSentenceTokenSelection(
                token_index=token_index,
                display_surface=display_surface,
                normalized_surface=normalized_surface,
                lemma_candidate=lemma_candidate,
                pos_tag=pos_tag,
                morphology=morphology,
                sentence_context=sentence_context,
                candidates=candidate_resolution.candidates,
            )
        if not should_generate_non_cor_sentence_token(pos_tag):
            return (
                save_root_level_sentence_token(
                    runtime,
                    token_index=token_index,
                    display_surface=display_surface,
                    normalized_surface=normalized_surface,
                    lemma=lemma_candidate,
                    pos_tag=pos_tag,
                    morphology=morphology,
                    cor_id=None,
                    gloss=None,
                    english_translation=None,
                    gloss_translation=None,
                    queue_verification=False,
                ),
                True,
            )
        return PendingGeneratedSentenceToken(
            token_index=token_index,
            display_surface=display_surface,
            normalized_surface=normalized_surface,
            lemma_candidate=lemma_candidate,
            pos_tag=pos_tag,
            morphology=morphology,
            sentence_context=sentence_context,
        )

    persisted_response = persist_candidate_to_wordbank(
        wordbank_use_case,
        normalized_surface=normalized_surface,
        candidate=selected_candidate,
    )
    if persisted_response is not None:
        persisted = sentence_token_from_saved_word(
            runtime,
            token_index=token_index,
            display_surface=display_surface,
            normalized_surface=normalized_surface,
            stored_lemma=selected_candidate.lemma,
            meaning_id=(
                persisted_response.meaning.id if persisted_response.meaning is not None else None
            ),
        )
        if persisted is not None:
            return persisted, True

    if candidate_resolution.is_ambiguous:
        return None

    return (
        save_root_level_sentence_token(
            runtime,
            token_index=token_index,
            display_surface=display_surface,
            normalized_surface=normalized_surface,
            lemma=selected_candidate.lemma,
            pos_tag=selected_candidate.pos_tag or pos_tag,
            morphology=selected_candidate.morphology or morphology,
            cor_id=selected_candidate.cor_id,
            gloss=selected_candidate.gloss,
            english_translation=selected_candidate.english_translation,
            gloss_translation=selected_candidate.gloss_translation,
            queue_verification=False,
        ),
        True,
    )


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
