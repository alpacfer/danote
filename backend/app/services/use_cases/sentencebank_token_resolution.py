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


def _ensure_mwe_meaning_section(
    runtime: WordbankRuntime,
    *,
    lemma: str,
    pos_tag: str | None,
    gloss: str | None,
    english_translation: str | None,
) -> None:
    from app.services.use_cases.wordbank.verification_targets import (
        discover_word_page_verification_targets,
        queue_verification_targets,
    )

    lexeme = runtime.repository.get_lexeme(lemma)
    if lexeme is None:
        return
    try:
        meaning_record, _inserted = runtime.repository.upsert_lexeme_meaning(
            lexeme_id=lexeme.id,
            meaning_key=normalize_token(lemma) or lemma,
            cor_lemma_idx=None,
            dictionary_status="generated_non_cor",
            gloss=gloss,
            english_translation=english_translation,
            pos_tag=pos_tag,
            morphology=None,
        )
    except LookupError:
        return
    runtime.repository.assign_orphan_surface_forms_to_meaning(
        lexeme_id=lexeme.id,
        meaning_id=meaning_record.id,
    )
    queue_verification_targets(
        runtime,
        stored_lemma=lemma,
        targets=discover_word_page_verification_targets(runtime, stored_lemma=lemma),
    )


def _infer_mwe_surface_morphology(
    runtime: WordbankRuntime,
    *,
    surface: str,
    lemma: str,
    pos_tag: str | None,
) -> str | None:
    if (pos_tag or "").upper() != "VERB":
        return None
    surface_parts = [part for part in surface.split() if part]
    lemma_parts = [part for part in lemma.split() if part]
    if not surface_parts or not lemma_parts:
        return None
    head_surface = surface_parts[0]
    head_lemma = lemma_parts[0]
    if not head_surface or not head_lemma:
        return None
    try:
        entries = runtime.cor.lookup_form(head_surface)
    except Exception:
        return None
    for entry in entries:
        if entry.pos_tag != "VERB" or entry.norm != "N":
            continue
        if normalize_token(entry.lemma) != head_lemma:
            continue
        if entry.morphology:
            return entry.morphology
    return None


@dataclass(frozen=True)
class MWEToken(NLPToken):
    pos_tag: str | None = None
    gloss: str | None = None
    english_translation: str | None = None



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


def align_tokens_to_source(sentence_tokens: list[NLPToken], source_text: str) -> list[tuple[NLPToken, int, int]]:
    aligned = []
    current_idx = 0
    for token in sentence_tokens:
        pos = source_text.find(token.text, current_idx)
        if pos == -1:
            pos = source_text.find(token.text, 0)
        if pos != -1:
            start = pos
            end = pos + len(token.text)
            aligned.append((token, start, end))
            current_idx = end
        else:
            aligned.append((token, current_idx, current_idx + len(token.text)))
            current_idx += len(token.text)
    return aligned


def merge_mwe_spans(
    sentence_tokens: list[NLPToken],
    source_text: str,
    mwe_spans: list[SentenceMWESpan] | None,
    runtime: WordbankRuntime | None = None,
) -> list[NLPToken]:
    if not mwe_spans:
        return sentence_tokens

    aligned = align_tokens_to_source(sentence_tokens, source_text)
    
    # Coalesce close spans pointing to the same normalized lemma and pos_tag
    coalesced_spans: list[SentenceMWESpan] = []
    spans_sorted = sorted(mwe_spans, key=lambda s: s.start)
    for span in spans_sorted:
        merged = False
        norm_lemma = normalize_token(span.lemma)
        norm_pos = (span.pos_tag or "").upper()
        
        for i, existing in enumerate(coalesced_spans):
            exist_lemma = normalize_token(existing.lemma)
            exist_pos = (existing.pos_tag or "").upper()
            
            if exist_lemma == norm_lemma and exist_pos == norm_pos:
                dist = span.start - existing.end
                if 0 <= dist <= 40:
                    coalesced_spans[i] = SentenceMWESpan(
                        start=min(existing.start, span.start),
                        end=max(existing.end, span.end),
                        surface=source_text[min(existing.start, span.start):max(existing.end, span.end)],
                        lemma=existing.lemma,
                        pos_tag=existing.pos_tag,
                        gloss=existing.gloss or span.gloss,
                        english_translation=existing.english_translation or span.english_translation,
                    )
                    merged = True
                    break
        if not merged:
            coalesced_spans.append(span)

    sorted_spans = sorted(coalesced_spans, key=lambda s: s.start, reverse=True)
    
    for span in sorted_spans:
        overlapping_indices = []
        for idx, (token, start, end) in enumerate(aligned):
            # Non-zero overlap check
            if max(start, span.start) < min(end, span.end):
                overlapping_indices.append(idx)
        
        if not overlapping_indices:
            continue
        
        lemma_words = {normalize_token(w) for w in span.lemma.split() if w}
        constituent_indices = []
        extra_indices = []
        
        # Words commonly inserted as intermediate elements in split phrasal verbs
        EXCLUDE_WORDS = {"ikke", "aldrig", "måske", "vist", "sgu", "da", "jo", "nok", "vel", "kun", "og", "eller", "men", "selv", "om"}
        
        for idx in overlapping_indices:
            token, start, end = aligned[idx]
            candidate_lemmas = {normalize_token(token.lemma), normalize_token(token.text)}
            
            if runtime is not None and hasattr(runtime, "cor") and runtime.cor is not None:
                try:
                    entries = runtime.cor.lookup_form(token.text)
                    for entry in entries:
                        candidate_lemmas.add(normalize_token(entry.lemma))
                except Exception:
                    pass
            
            is_constituent = any(lem in lemma_words for lem in candidate_lemmas if lem)
            
            if not is_constituent:
                tok_text_norm = normalize_token(token.text)
                if tok_text_norm not in EXCLUDE_WORDS and not token.is_punctuation:
                    is_constituent = True
                
            if is_constituent:
                constituent_indices.append(idx)
            else:
                extra_indices.append(idx)
        
        if not constituent_indices:
            continue
            
        constituent_tokens_sorted = sorted([aligned[i] for i in constituent_indices], key=lambda x: x[1])
        extra_tokens_sorted = sorted([aligned[i] for i in extra_indices], key=lambda x: x[1])
        
        merged_surface = " ".join(t[0].text for t in constituent_tokens_sorted)
        
        mwe_pos = span.pos_tag or "VERB"
        mwe_token = MWEToken(
            text=merged_surface,
            lemma=span.lemma,
            pos=mwe_pos,
            morphology=None,
            is_punctuation=False,
            pos_tag=mwe_pos,
            gloss=span.gloss,
            english_translation=span.english_translation,
        )
        
        first_idx = overlapping_indices[0]
        last_idx = overlapping_indices[-1]
        
        replacement = [(mwe_token, span.start, span.end)]
        for extra_tok, ext_start, ext_end in extra_tokens_sorted:
            replacement.append((extra_tok, ext_start, ext_end))
            
        aligned[first_idx : last_idx + 1] = replacement
        
    return [t[0] for t in aligned]


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
            surface_morphology = _infer_mwe_surface_morphology(
                runtime,
                surface=normalized_surface,
                lemma=lemma_candidate,
                pos_tag=mwe_pos_tag,
            )
            if existing is not None:
                runtime.related_words.write_mwe_component_related_words(
                    stored_lemma=lemma_candidate,
                )
                if surface_morphology:
                    lexeme = runtime.repository.get_lexeme(lemma_candidate)
                    if lexeme is not None:
                        runtime.repository.insert_or_update_surface_form(
                            lexeme_id=lexeme.id,
                            meaning_id=None,
                            form=normalized_surface,
                            pos_tag=mwe_pos_tag,
                            morphology=surface_morphology,
                            source="search",
                        )
                _ensure_mwe_meaning_section(
                    runtime,
                    lemma=lemma_candidate,
                    pos_tag=mwe_pos_tag,
                    gloss=nlp_token.gloss,
                    english_translation=nlp_token.english_translation,
                )
                planned_tokens.append((existing, False))
                continue

            cor_entry = runtime.cor.lookup_mwe_lemma(lemma_candidate)
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
            )
            if surface_morphology:
                lexeme = runtime.repository.get_lexeme(lemma_candidate)
                if lexeme is not None:
                    runtime.repository.insert_or_update_surface_form(
                        lexeme_id=lexeme.id,
                        meaning_id=None,
                        form=normalized_surface,
                        pos_tag=mwe_pos_tag,
                        morphology=surface_morphology,
                        source="search",
                    )
            runtime.related_words.write_mwe_component_related_words(
                stored_lemma=lemma_candidate,
            )
            _ensure_mwe_meaning_section(
                runtime,
                lemma=lemma_candidate,
                pos_tag=mwe_pos_tag,
                gloss=nlp_token.gloss,
                english_translation=nlp_token.english_translation,
            )
            planned_tokens.append((mwe_record, False))
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
