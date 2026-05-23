from __future__ import annotations

import re
from dataclasses import dataclass

from app.db.repositories.sentencebank import SentenceTokenWriteRecord
from app.nlp.adapter import NLPToken
from app.nlp.token_filter import is_wordlike_token
from app.services.concurrency import run_in_parallel
from app.services.gemini_translation import NonCORWordGenerationInput, NonCORWordGenerationResult
from app.services.sentence_verification import SentenceMWESpan
from app.services.token_classifier import normalize_token
from app.services.use_cases.sentencebank_candidates import (
    SentenceMeaningCandidate,
    select_sentence_candidate,
)
from app.services.use_cases.sentencebank_contextual_translations import is_existential_der_context
from app.services.use_cases.sentencebank_mwe import (
    MWEToken,
    ensure_mwe_meaning_section,
    infer_mwe_surface_morphology,
    merge_mwe_spans,
    upsert_mwe_surface_form_preserving_meaning,
)
from app.services.use_cases.sentencebank_text import should_skip_sentence_wordbank_token
from app.services.use_cases.sentencebank_token_persistence import (
    existing_saved_token,
    persist_candidate_to_wordbank,
    persist_generated_to_wordbank,
    save_root_level_sentence_token,
    save_static_builtin_sentence_token,
    save_static_hv_word_sentence_token,
    save_static_pronoun_sentence_token,
    sentence_token_from_saved_word,
    unsaved_sentence_token,
    verification_metadata_for_new_sentence_token,
)
from app.services.use_cases.wordbank.runtime import WordbankRuntime


from app.services.use_cases.sentencebank_token_resolution_helpers import (
    PendingGeneratedSentenceToken,
    PendingSentenceTokenSelection,
    _should_prefer_static_builtin,
    batch_generate_non_cor_sentence_tokens,
    batch_select_sentence_candidates,
    finalize_generated_sentence_token,
    finalize_pending_sentence_token,
    should_generate_non_cor_sentence_token,
    should_use_static_pronoun_sentence_token,
)


def resolve_sentence_tokens(
    runtime: WordbankRuntime | None,
    *,
    source_text: str,
    nlp_adapter,
    wordbank_use_case,
    mwe_spans: list[SentenceMWESpan] | None = None,
) -> tuple[list[SentenceTokenWriteRecord], list[dict[str, object]]]:
    if runtime is None or wordbank_use_case is None:
        return [], []

    sentence_tokens = (
        nlp_adapter.tokenize(source_text)
        if nlp_adapter is not None
        else fallback_sentence_tokens(source_text)
    )
    if mwe_spans:
        sentence_tokens = merge_mwe_spans(sentence_tokens, source_text, mwe_spans, runtime)

    pending_selection_results: dict[int, SentenceMeaningCandidate | None] = {}
    pending_selections: list[PendingSentenceTokenSelection] = []
    pending_generation_results: dict[int, NonCORWordGenerationResult | None] = {}
    pending_generations: list[PendingGeneratedSentenceToken] = []
    planned_tokens: list[
        tuple[SentenceTokenWriteRecord, bool] | PendingSentenceTokenSelection | PendingGeneratedSentenceToken
    ] = []
    new_tokens: list[dict[str, object]] = []
    for nlp_token in sentence_tokens:
        if isinstance(nlp_token, MWEToken):
            surface_form = nlp_token.text.strip()
            normalized_surface = normalize_token(surface_form)
            lemma_candidate = normalize_token(nlp_token.lemma or "") or normalized_surface

            existing = existing_saved_token(
                runtime,
                display_surface=surface_form,
                normalized_surface=normalized_surface,
                lemma_candidate=lemma_candidate,
                token_index=len(planned_tokens),
                pos_tag=nlp_token.pos_tag,
                sentence_context=source_text,
            )
            mwe_pos_tag = (nlp_token.pos_tag or "VERB").upper()
            surface_morphology = infer_mwe_surface_morphology(
                runtime,
                surface=normalized_surface,
                lemma=lemma_candidate,
                pos_tag=mwe_pos_tag,
            )
            cor_entry = runtime.cor.lookup_mwe_lemma(lemma_candidate)

            if existing is None:
                cor_id = cor_entry.cor_id if cor_entry is not None else None
                mwe_record = save_root_level_sentence_token(
                    runtime,
                    token_index=len(planned_tokens),
                    display_surface=surface_form,
                    normalized_surface=normalized_surface,
                    lemma=lemma_candidate,
                    pos_tag=mwe_pos_tag,
                    morphology=None,
                    cor_id=cor_id,
                    gloss=nlp_token.gloss,
                    english_translation=nlp_token.english_translation,
                    gloss_translation=None,
                    lexeme_translation=nlp_token.english_translation,
                    lexeme_translation_provider="gemini",
                    # Verification is queued by ensure_mwe_meaning_section below, after
                    # the meaning exists so the discovery walk picks up meaning-level
                    # targets in a single pass. Suppress the redundant root-level queue.
                    queue_verification=False,
                    # Set the lexeme's dictionary_status so the Gemini related-words
                    # worker keeps ADP/CCONJ constituents (e.g. "på") that don't
                    # match a COR entry. See process_queued_resolution in
                    # collaborators/related_words.py — it drops candidate-less items
                    # unless the lexeme is "cor" or "generated_non_cor".
                    dictionary_status="cor" if cor_entry is not None else "generated_non_cor",
                )
                planned_token = (mwe_record, False)
            else:
                planned_token = (existing, False)

            if surface_morphology:
                upsert_mwe_surface_form_preserving_meaning(
                    runtime,
                    lemma=lemma_candidate,
                    form=normalized_surface,
                    pos_tag=mwe_pos_tag,
                    morphology=surface_morphology,
                )
            runtime.related_words.seed_mwe_component_related_words(
                stored_lemma=lemma_candidate,
            )
            ensure_mwe_meaning_section(
                runtime,
                lemma=lemma_candidate,
                pos_tag=mwe_pos_tag,
                gloss=nlp_token.gloss,
                english_translation=nlp_token.english_translation,
                cor_entry=cor_entry,
            )
            planned_tokens.append(planned_token)
            continue

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
    should_prefer_static_builtin = _should_prefer_static_builtin(
        normalized_surface=normalized_surface,
        pos_tag=pos_tag,
        sentence_context=sentence_context,
    )
    if should_prefer_static_builtin:
        static_builtin = save_static_builtin_sentence_token(
            runtime,
            token_index=token_index,
            display_surface=display_surface,
            normalized_surface=normalized_surface,
            pos_tag=pos_tag,
            morphology=morphology,
            sentence_context=sentence_context,
        )
        if static_builtin is not None:
            return static_builtin

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

