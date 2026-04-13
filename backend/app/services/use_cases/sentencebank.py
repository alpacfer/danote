from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.api.schemas.v1.sentencebank import (
    AddSentenceResponse,
    SentenceListResponse,
    SentenceSearchPreviewResponse,
    SentenceSummary,
    SentenceTokenCard,
    SentenceVerificationErrorItem,
    VerifySentenceResponse,
)
from app.db.repositories import SentencebankRepository
from app.db.repositories.sentencebank import SentenceRecord, SentenceTokenWriteRecord
from app.nlp.adapter import NLPAdapter
from app.nlp.token_filter import is_wordlike_token
from app.services.cor_local import CORLocalEntry
from app.services.sentence_verification import (
    SentenceVerificationResult,
    SentenceVerificationService,
)
from app.services.token_classifier import normalize_token
from app.services.translation import TranslationService
from app.services.use_cases.wordbank import WordbankUseCase
from app.services.use_cases.wordbank.collaborators.cor_local_translations import (
    lookup_translation_for_cor_local_entry,
)
from app.services.use_cases.wordbank.gloss_translations import meaning_gloss_translation
from app.services.use_cases.wordbank.pronunciation_queue import queue_pronunciation_generation
from app.services.use_cases.wordbank.related_words_queue import queue_related_words_resolution
from app.services.use_cases.wordbank.runtime import WordbankRuntime
from app.services.use_cases.wordbank.verification_targets import (
    discover_word_page_verification_targets,
    queue_verification_targets,
)
from app.services.verification import WordVerificationInput


def _normalize_sentence_text(source_text: str) -> str:
    return " ".join(source_text.strip().split())


def _capitalize_sentence_translation(english_translation: str | None) -> str | None:
    if not isinstance(english_translation, str):
        return None
    cleaned = " ".join(english_translation.strip().split())
    if not cleaned:
        return None

    alpha_index = next((idx for idx, char in enumerate(cleaned) if char.isalpha()), None)
    if alpha_index is None or cleaned[alpha_index].isupper():
        return cleaned
    return cleaned[:alpha_index] + cleaned[alpha_index].upper() + cleaned[alpha_index + 1:]


def _normalize_query_language(value: str | None) -> Literal["da", "en", "unknown"]:
    cleaned = value.strip().lower() if isinstance(value, str) else ""
    if cleaned == "da":
        return "da"
    if cleaned == "en":
        return "en"
    return "unknown"


def _starts_with_uppercase_letter(text: str) -> bool:
    for char in text:
        if char.isalpha():
            return char.isupper()
    return False


def _has_internal_uppercase_letter(text: str) -> bool:
    seen_alpha = False
    for char in text:
        if not char.isalpha():
            continue
        if seen_alpha and char.isupper():
            return True
        seen_alpha = True
    return False


def _should_skip_sentence_wordbank_token(
    *,
    surface_form: str,
    lemma_candidate: str,
    pos_tag: str | None,
    token_index: int,
) -> bool:
    if (pos_tag or "").strip().upper() == "PROPN":
        return True
    if token_index > 0 and _starts_with_uppercase_letter(surface_form):
        return True
    return _has_internal_uppercase_letter(surface_form) or _has_internal_uppercase_letter(lemma_candidate)


@dataclass(frozen=True, slots=True)
class _SentenceMeaningCandidate:
    id: int
    lemma: str
    meaning_key: str
    cor_lemma_idx: int | None
    gloss: str | None
    english_translation: str | None
    gloss_translation: str | None
    pos_tag: str | None
    morphology: str | None
    cor_id: str | None


@dataclass(frozen=True, slots=True)
class _SentenceCandidateResolution:
    candidate: _SentenceMeaningCandidate | None
    is_ambiguous: bool
    candidates: tuple[_SentenceMeaningCandidate, ...] = ()


@dataclass(frozen=True, slots=True)
class _PendingSentenceTokenSelection:
    token_index: int
    display_surface: str
    normalized_surface: str
    lemma_candidate: str
    pos_tag: str | None
    morphology: str | None
    sentence_context: str
    candidates: tuple[_SentenceMeaningCandidate, ...]


class SentencebankUseCase:
    def __init__(
        self,
        db_path,
        translation_service: TranslationService | None = None,
        nlp_adapter: NLPAdapter | None = None,
        wordbank_use_case: WordbankUseCase | None = None,
        sentence_verification_service: SentenceVerificationService | None = None,
    ):
        self._repository = SentencebankRepository(db_path)
        self._translation_service = translation_service
        self._nlp_adapter = nlp_adapter
        self._wordbank_use_case = wordbank_use_case
        self._sentence_verification_service = sentence_verification_service

    def add_sentence(self, source_text: str) -> AddSentenceResponse:
        normalized_source_text = _normalize_sentence_text(source_text)
        normalized_key = normalize_token(source_text)
        if not normalized_source_text or not normalized_key:
            raise ValueError("source_text is required")

        existing = self._repository.find_by_normalized_sentence(normalized_key)
        if existing is not None:
            return _sentence_response(
                existing,
                status="exists",
                message=f'"{existing.source_text}" is already in sentencebank.',
            )

        english_translation = self._lookup_phrase_translation(normalized_source_text)
        provider = self._translation_provider_name()
        sentence_id = self._repository.insert_sentence(
            source_text=normalized_source_text,
            normalized_sentence=normalized_key,
            english_translation=english_translation,
            translation_provider=provider if english_translation else None,
        )
        token_records, new_token_metadata = self._resolve_sentence_tokens(normalized_source_text)
        self._repository.replace_sentence_tokens(sentence_id=sentence_id, tokens=token_records)
        if new_token_metadata and self._wordbank_use_case is not None:
            _batch_verify_new_sentence_tokens(
                self._wordbank_use_case.runtime,
                new_token_metadata=new_token_metadata,
                sentence_context=normalized_source_text,
            )
        saved = self._repository.find_by_normalized_sentence(normalized_key)
        if saved is None:
            raise RuntimeError("Sentence was saved but could not be reloaded.")
        return _sentence_response(
            saved,
            status="inserted",
            message=f'Added "{normalized_source_text}" to sentencebank.',
        )

    def list_sentences(self) -> SentenceListResponse:
        rows = self._repository.list_sentences()
        return SentenceListResponse(items=[_sentence_summary(row) for row in rows])

    def list_linked_sentences(self, stored_lemma: str) -> list[SentenceSummary]:
        normalized_lemma = normalize_token(stored_lemma)
        if not normalized_lemma:
            return []
        return [_sentence_summary(row) for row in self._repository.list_linked_sentences_for_lemma(normalized_lemma)]

    def verify_sentence(self, source_text: str) -> VerifySentenceResponse:
        normalized = _normalize_sentence_text(source_text)
        if not normalized:
            raise ValueError("source_text is required")
        if self._sentence_verification_service is None:
            return VerifySentenceResponse(is_valid=True, errors=[], corrected_text=None, language="unknown")
        result = self._sentence_verification_service.verify_sentence(normalized)
        return VerifySentenceResponse(
            is_valid=result.is_valid,
            errors=[
                SentenceVerificationErrorItem(start=e.start, end=e.end, message=e.message)
                for e in result.errors
            ],
            corrected_text=result.corrected_text,
            language=result.language,
        )

    def preview_sentence_search(self, source_text: str) -> SentenceSearchPreviewResponse:
        normalized_query = _normalize_sentence_text(source_text)
        if not normalized_query:
            raise ValueError("source_text is required")

        initial_verification = self._verify_sentence_result(normalized_query)
        query_language = initial_verification.language
        if query_language == "unknown":
            query_language = self._detect_query_language(normalized_query)

        if query_language == "en":
            translated_danish = self._lookup_reverse_translation(normalized_query)
            if not translated_danish:
                return SentenceSearchPreviewResponse(
                    status="blocked",
                    query_language="en",
                    source_text=None,
                    english_translation=None,
                    is_valid=False,
                    errors=[],
                    message="Could not translate this English sentence to Danish.",
                )
            verification = self._verify_sentence_result(translated_danish)
            final_source_text = verification.corrected_text or translated_danish
            return SentenceSearchPreviewResponse(
                status="ready",
                query_language="en",
                source_text=final_source_text,
                english_translation=self._lookup_phrase_translation(final_source_text),
                is_valid=verification.is_valid,
                errors=[
                    SentenceVerificationErrorItem(start=e.start, end=e.end, message=e.message)
                    for e in verification.errors
                ],
                message=None,
            )

        final_source_text = initial_verification.corrected_text or normalized_query
        return SentenceSearchPreviewResponse(
            status="ready",
            query_language=query_language,
            source_text=final_source_text,
            english_translation=self._lookup_phrase_translation(final_source_text),
            is_valid=initial_verification.is_valid,
            errors=[
                SentenceVerificationErrorItem(start=e.start, end=e.end, message=e.message)
                for e in initial_verification.errors
            ],
            message=None,
        )

    def _lookup_phrase_translation(self, source_text: str) -> str | None:
        if self._wordbank_use_case is not None:
            try:
                payload = self._wordbank_use_case.generate_phrase_translation(source_text)
                if payload.english_translation:
                    return payload.english_translation
            except Exception:
                pass
        if self._translation_service is None:
            return None
        try:
            translated = self._translation_service.translate_da_to_en(source_text)
            if not isinstance(translated, str):
                return None
            return _capitalize_sentence_translation(translated)
        except Exception:
            return None

    def _lookup_reverse_translation(self, source_text: str) -> str | None:
        if self._translation_service is None:
            return None
        translate_en_to_da = getattr(self._translation_service, "translate_en_to_da", None)
        if not callable(translate_en_to_da):
            return None
        try:
            translated = translate_en_to_da(source_text)
            return _normalize_sentence_text(translated) if isinstance(translated, str) and translated.strip() else None
        except Exception:
            return None

    def _detect_query_language(self, source_text: str) -> Literal["da", "en", "unknown"]:
        if self._translation_service is None:
            return "unknown"
        detect_source_language = getattr(self._translation_service, "detect_source_language", None)
        if not callable(detect_source_language):
            return "unknown"
        try:
            return _normalize_query_language(detect_source_language(source_text))
        except Exception:
            return "unknown"

    def _verify_sentence_result(self, source_text: str):
        if self._sentence_verification_service is None:
            return SentenceVerificationResult(
                is_valid=True,
                errors=[],
                corrected_text=None,
                language="unknown",
            )
        try:
            return self._sentence_verification_service.verify_sentence(source_text)
        except Exception:
            return SentenceVerificationResult(
                is_valid=True,
                errors=[],
                corrected_text=None,
                language="unknown",
            )

    def _translation_provider_name(self) -> str:
        provider = getattr(self._translation_service, "provider", None)
        if isinstance(provider, str):
            cleaned = provider.strip().lower()
            if cleaned:
                return cleaned
        return "translation"

    def _resolve_sentence_tokens(self, source_text: str) -> tuple[list[SentenceTokenWriteRecord], list[dict[str, object]]]:
        """Returns (token_records, new_token_metadata)."""
        if self._nlp_adapter is None or self._wordbank_use_case is None:
            return [], []
        runtime = self._wordbank_use_case.runtime
        pending_selection_results: dict[int, _SentenceMeaningCandidate | None] = {}
        pending_selections: list[_PendingSentenceTokenSelection] = []
        planned_tokens: list[tuple[SentenceTokenWriteRecord, bool] | _PendingSentenceTokenSelection] = []
        new_tokens: list[dict[str, object]] = []
        for nlp_token in self._nlp_adapter.tokenize(source_text):
            surface_form = nlp_token.text.strip()
            if not surface_form or nlp_token.is_punctuation:
                continue
            if not is_wordlike_token(surface_form):
                continue
            raw_lemma_candidate = (nlp_token.lemma or "").strip()
            if _should_skip_sentence_wordbank_token(
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
            resolved_token = self._resolve_sentence_token(
                runtime,
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
            if isinstance(resolved_token, _PendingSentenceTokenSelection):
                pending_selections.append(resolved_token)
                planned_tokens.append(resolved_token)
                continue
            planned_tokens.append(resolved_token)

        if pending_selections:
            selected_candidates = _batch_select_sentence_candidates(runtime, pending_selections)
            for selection, selected_candidate in zip(pending_selections, selected_candidates, strict=False):
                pending_selection_results[selection.token_index] = selected_candidate

        resolved: list[SentenceTokenWriteRecord] = []
        seen_verification_targets: set[tuple[str, str | None, int | None]] = set()
        for planned_token in planned_tokens:
            if isinstance(planned_token, _PendingSentenceTokenSelection):
                selected_candidate = pending_selection_results.get(planned_token.token_index)
                resolved_token = _finalize_pending_sentence_token(
                    self._wordbank_use_case,
                    runtime,
                    selection=planned_token,
                    selected_candidate=selected_candidate,
                )
                if resolved_token is None:
                    continue
                token, is_new = resolved_token
            else:
                token, is_new = planned_token
            resolved.append(token)
            if is_new:
                for metadata in _verification_metadata_for_new_sentence_token(token):
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

    def _resolve_sentence_token(
        self,
        runtime: WordbankRuntime,
        *,
        token_index: int,
        display_surface: str,
        normalized_surface: str,
        lemma_candidate: str,
        pos_tag: str | None,
        morphology: str | None,
        sentence_context: str,
    ) -> tuple[SentenceTokenWriteRecord, bool] | _PendingSentenceTokenSelection | None:
        existing = _existing_saved_token(
            runtime,
            display_surface=display_surface,
            normalized_surface=normalized_surface,
            lemma_candidate=lemma_candidate,
            token_index=token_index,
        )
        if existing is not None:
            return existing, False

        candidate_resolution = _select_sentence_candidate(
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
                return _PendingSentenceTokenSelection(
                    token_index=token_index,
                    display_surface=display_surface,
                    normalized_surface=normalized_surface,
                    lemma_candidate=lemma_candidate,
                    pos_tag=pos_tag,
                    morphology=morphology,
                    sentence_context=sentence_context,
                    candidates=candidate_resolution.candidates,
                )
            return _save_root_level_sentence_token(
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
            ), True

        persisted_response = _persist_candidate_to_wordbank(
            self._wordbank_use_case,
            normalized_surface=normalized_surface,
            candidate=selected_candidate,
        )
        if persisted_response is not None:
            persisted = _sentence_token_from_saved_word(
                runtime,
                token_index=token_index,
                display_surface=display_surface,
                normalized_surface=normalized_surface,
                stored_lemma=selected_candidate.lemma,
                meaning_id=(
                    persisted_response.meaning.id
                    if persisted_response.meaning is not None
                    else None
                ),
            )
            if persisted is not None:
                return persisted, True

        if candidate_resolution.is_ambiguous:
            return None

        return _save_root_level_sentence_token(
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
        ), True


def _persist_candidate_to_wordbank(
    wordbank_use_case: WordbankUseCase | None,
    *,
    normalized_surface: str,
    candidate: _SentenceMeaningCandidate,
) -> object | None:
    if wordbank_use_case is None:
        return None
    try:
        return wordbank_use_case.add_word(
            normalized_surface,
            candidate.lemma,
            queue_verification=False,
            search_seed={
                "lemma": candidate.lemma,
                "surface": normalized_surface,
                "cor_id": candidate.cor_id,
                "cor_lemma_idx": candidate.cor_lemma_idx,
                "meaning_key": candidate.meaning_key,
                "gloss": candidate.gloss,
                "english_translation": candidate.english_translation,
                "pos_tag": candidate.pos_tag,
                "morphology": candidate.morphology,
            },
        )
    except Exception:
        return None


def _existing_saved_token(
    runtime: WordbankRuntime,
    *,
    display_surface: str,
    normalized_surface: str,
    lemma_candidate: str,
    token_index: int,
) -> SentenceTokenWriteRecord | None:
    saved_variation = runtime.repository.find_saved_variation_translation_target(normalized_surface)
    if saved_variation is not None:
        return _sentence_token_from_saved_word(
            runtime,
            token_index=token_index,
            display_surface=display_surface,
            normalized_surface=normalized_surface,
            stored_lemma=saved_variation.lemma,
            meaning_id=saved_variation.meaning_id,
        )
    if normalized_surface == lemma_candidate:
        saved_lemma = runtime.repository.find_saved_lemma_translation_target(lemma_candidate)
        if saved_lemma is not None:
            return _sentence_token_from_saved_word(
                runtime,
                token_index=token_index,
                display_surface=display_surface,
                normalized_surface=normalized_surface,
                stored_lemma=saved_lemma.lemma,
                meaning_id=saved_lemma.meaning_id,
            )
    return None


def _sentence_token_from_saved_word(
    runtime: WordbankRuntime,
    *,
    token_index: int,
    display_surface: str,
    normalized_surface: str,
    stored_lemma: str,
    meaning_id: int | None,
) -> SentenceTokenWriteRecord | None:
    lexeme = runtime.repository.get_lexeme(stored_lemma)
    if lexeme is None:
        return None
    meaning = runtime.repository.get_lexeme_meaning(meaning_id) if meaning_id is not None else None
    surface_row = _matching_surface_form_row(
        runtime,
        lexeme_id=lexeme.id,
        normalized_surface=normalized_surface,
        meaning_id=meaning_id,
    )
    gloss_translation_cache: dict[
        tuple[str, str, str | None, str | None, str, str | None, str | None],
        str | None,
    ] = {}
    return SentenceTokenWriteRecord(
        token_index=token_index,
        surface_form=display_surface,
        normalized_surface=normalized_surface,
        stored_lemma=stored_lemma,
        lexeme_id=lexeme.id,
        meaning_id=meaning.id if meaning is not None else None,
        cor_id=surface_row.cor_id if surface_row is not None else None,
        pos_tag=(
            (surface_row.pos_tag if surface_row is not None else None)
            or (meaning.pos_tag if meaning is not None else None)
            or lexeme.pos_tag
        ),
        morphology=(
            (surface_row.morphology if surface_row is not None else None)
            or (meaning.morphology if meaning is not None else None)
            or lexeme.morphology
        ),
        gloss=meaning.gloss if meaning is not None else None,
        english_translation=(
            meaning.english_translation if meaning is not None else lexeme.english_translation
        ),
        gloss_translation=(
            meaning_gloss_translation(
                runtime,
                lexeme_lemma=lexeme.lemma,
                lexeme_pos_tag=lexeme.pos_tag,
                meaning_gloss=meaning.gloss,
                meaning_translation=meaning.english_translation,
                meaning_pos_tag=meaning.pos_tag,
                cor_lemma_idx=meaning.cor_lemma_idx,
                cache=gloss_translation_cache,
            )
            if meaning is not None
            else None
        ),
    )


def _save_root_level_sentence_token(
    runtime: WordbankRuntime,
    *,
    token_index: int,
    display_surface: str,
    normalized_surface: str,
    lemma: str,
    pos_tag: str | None,
    morphology: str | None,
    cor_id: str | None,
    gloss: str | None,
    english_translation: str | None,
    gloss_translation: str | None,
    queue_verification: bool = True,
) -> SentenceTokenWriteRecord:
    lexeme_id, _inserted_lexeme = runtime.repository.insert_or_load_lexeme(
        stored_lemma=lemma,
        translation=None,
        provider=None,
        pos_tag=pos_tag,
        morphology=morphology,
        source="search",
    )
    surface_form, _inserted_surface_form = runtime.repository.insert_or_update_surface_form(
        lexeme_id=lexeme_id,
        meaning_id=None,
        form=normalized_surface,
        pos_tag=pos_tag,
        morphology=morphology,
        source="search",
    )
    if cor_id:
        runtime.repository.insert_surface_form_cor_variant(
            surface_form_id=surface_form.id,
            cor_id=cor_id,
        )
    runtime.nlp.add_user_lexeme(lemma)
    runtime.nlp.invalidate_pos_cache(lemma, normalized_surface)
    if queue_verification:
        queue_verification_targets(
            runtime,
            stored_lemma=lemma,
            targets=discover_word_page_verification_targets(runtime, stored_lemma=lemma),
        )
    queue_pronunciation_generation(
        runtime,
        stored_lemma=lemma,
        requested_forms=(normalized_surface,),
    )
    queue_related_words_resolution(runtime, stored_lemma=lemma)
    return SentenceTokenWriteRecord(
        token_index=token_index,
        surface_form=display_surface,
        normalized_surface=normalized_surface,
        stored_lemma=lemma,
        lexeme_id=lexeme_id,
        meaning_id=None,
        cor_id=cor_id,
        pos_tag=pos_tag,
        morphology=morphology,
        gloss=gloss,
        english_translation=english_translation,
        gloss_translation=gloss_translation,
    )


def _batch_verify_new_sentence_tokens(
    runtime: WordbankRuntime,
    *,
    new_token_metadata: list[dict[str, object]],
    sentence_context: str,
) -> None:
    """Batch-verify newly persisted sentence tokens via single Gemini call."""
    verification_pairs = [
        (meta, _build_verification_input(runtime, meta))
        for meta in new_token_metadata
    ]
    fallback_metadata = [meta for meta, verification_input in verification_pairs if verification_input is None]
    valid_pairs = [(meta, verification_input) for meta, verification_input in verification_pairs if verification_input is not None]
    valid_inputs = [verification_input for _meta, verification_input in valid_pairs]
    if fallback_metadata:
        _queue_sentence_token_verification_fallback(runtime, fallback_metadata)
    if not valid_inputs:
        return
    try:
        results = runtime.verification.verify_word_entries_batch(
            valid_inputs, sentence_context=sentence_context,
        )
        error_metadata = [
            meta
            for (meta, _verification_input), result in zip(valid_pairs, results, strict=False)
            if result.status == "error"
        ]
        if error_metadata:
            _queue_sentence_token_verification_fallback(runtime, error_metadata)
    except Exception:
        _queue_sentence_token_verification_fallback(runtime, new_token_metadata)


def _queue_sentence_token_verification_fallback(
    runtime: WordbankRuntime,
    metadata_items: list[dict[str, object]],
) -> None:
    queued_lemmas: set[str] = set()
    for meta in metadata_items:
        stored_lemma = normalize_token(str(meta.get("stored_lemma", "")))
        if not stored_lemma or stored_lemma in queued_lemmas:
            continue
        queued_lemmas.add(stored_lemma)
        queue_verification_targets(
            runtime,
            stored_lemma=stored_lemma,
            targets=discover_word_page_verification_targets(runtime, stored_lemma=stored_lemma),
        )


def _build_verification_input(
    runtime: WordbankRuntime,
    meta: dict[str, object],
) -> WordVerificationInput | None:
    from app.services.use_cases.wordbank.verification_input_builder import build_verification_input

    stored_lemma = str(meta.get("stored_lemma", ""))
    stored_surface_form = meta.get("stored_surface_form")
    meaning_id = meta.get("meaning_id")
    if not stored_lemma:
        return None
    normalized_surface_form = str(stored_surface_form) if stored_surface_form else None
    if normalized_surface_form == stored_lemma:
        normalized_surface_form = None
    return build_verification_input(
        db_path=runtime.verification._db_path,
        nlp=runtime.nlp,
        cor=runtime.cor,
        stored_lemma=stored_lemma,
        stored_surface_form=normalized_surface_form,
        meaning_id=int(meaning_id) if isinstance(meaning_id, int) and meaning_id else None,
    )


def _verification_metadata_for_new_sentence_token(
    token: SentenceTokenWriteRecord,
) -> list[dict[str, object]]:
    root_target = {
        "stored_lemma": token.stored_lemma,
        "stored_surface_form": None,
        "meaning_id": token.meaning_id,
    }
    if token.meaning_id is not None or token.normalized_surface == token.stored_lemma:
        return [root_target]
    return [
        root_target,
        {
            "stored_lemma": token.stored_lemma,
            "stored_surface_form": token.normalized_surface,
            "meaning_id": None,
        },
    ]


def _batch_select_sentence_candidates(
    runtime: WordbankRuntime,
    pending_selections: list[_PendingSentenceTokenSelection],
) -> list[_SentenceMeaningCandidate | None]:
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
    resolved: list[_SentenceMeaningCandidate | None] = []
    for selection, selected_id in zip(pending_selections, selected_ids, strict=False):
        resolved.append(
            next((candidate for candidate in selection.candidates if candidate.id == selected_id), None)
        )
    if len(resolved) < len(pending_selections):
        resolved.extend([None] * (len(pending_selections) - len(resolved)))
    return resolved


def _finalize_pending_sentence_token(
    wordbank_use_case: WordbankUseCase | None,
    runtime: WordbankRuntime,
    *,
    selection: _PendingSentenceTokenSelection,
    selected_candidate: _SentenceMeaningCandidate | None,
) -> tuple[SentenceTokenWriteRecord, bool] | None:
    if selected_candidate is None:
        return None
    persisted_response = _persist_candidate_to_wordbank(
        wordbank_use_case,
        normalized_surface=selection.normalized_surface,
        candidate=selected_candidate,
    )
    if persisted_response is not None:
        persisted = _sentence_token_from_saved_word(
            runtime,
            token_index=selection.token_index,
            display_surface=selection.display_surface,
            normalized_surface=selection.normalized_surface,
            stored_lemma=selected_candidate.lemma,
            meaning_id=(
                persisted_response.meaning.id
                if persisted_response.meaning is not None
                else None
            ),
        )
        if persisted is not None:
            return persisted, True

    return _save_root_level_sentence_token(
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
    ), True


def _select_sentence_candidate(
    runtime: WordbankRuntime,
    *,
    surface_form: str,
    lemma_candidate: str,
    pos_tag: str | None,
    morphology: str | None,
    sentence_context: str,
) -> _SentenceCandidateResolution:
    entries = _candidate_entries_for_sentence_token(
        runtime,
        surface_form=surface_form,
        lemma_candidate=lemma_candidate,
        pos_tag=pos_tag,
    )
    if not entries:
        return _SentenceCandidateResolution(candidate=None, is_ambiguous=False, candidates=())
    candidates = _group_sentence_candidates(runtime, entries=entries)
    if not candidates:
        return _SentenceCandidateResolution(candidate=None, is_ambiguous=False, candidates=())
    if len(candidates) == 1:
        return _SentenceCandidateResolution(candidate=candidates[0], is_ambiguous=False, candidates=tuple(candidates))
    return _SentenceCandidateResolution(candidate=None, is_ambiguous=True, candidates=tuple(candidates))


def _candidate_entries_for_sentence_token(
    runtime: WordbankRuntime,
    *,
    surface_form: str,
    lemma_candidate: str,
    pos_tag: str | None,
) -> list[CORLocalEntry]:
    entries: list[CORLocalEntry] = []
    seen: set[str] = set()
    candidate_lemmas = [lemma_candidate]
    if surface_form != lemma_candidate:
        candidate_lemmas.append(surface_form)
    for preferred_pos_tag in (pos_tag, None):
        for lemma in candidate_lemmas:
            for entry in runtime.cor.cor_local_entries_for_form(
                form=surface_form,
                lemma=lemma,
                preferred_pos_tag=preferred_pos_tag,
            ):
                if entry.cor_id in seen:
                    continue
                seen.add(entry.cor_id)
                entries.append(entry)
        for entry in runtime.cor.cor_local_entries_for_surface_form(
            form=surface_form,
            preferred_pos_tag=preferred_pos_tag,
        ):
            if entry.cor_id in seen:
                continue
            seen.add(entry.cor_id)
            entries.append(entry)
        if entries:
            break
    return entries


def _group_sentence_candidates(
    runtime: WordbankRuntime,
    *,
    entries: list[CORLocalEntry],
) -> list[_SentenceMeaningCandidate]:
    grouped: dict[tuple[str, int | None, str | None, str | None], CORLocalEntry] = {}
    for entry in entries:
        key = (
            entry.lemma,
            entry.lemma_idx,
            normalize_token(entry.gloss or "") or None,
            entry.pos_tag,
        )
        grouped.setdefault(key, entry)
    candidates: list[_SentenceMeaningCandidate] = []
    for index, entry in enumerate(grouped.values(), start=1):
        english_translation = lookup_translation_for_cor_local_entry(runtime.translation, entry)
        gloss_translation = runtime.cor.lookup_translation_for_cor_gloss(
            entry=entry,
            lemma_translation=english_translation,
            cache={},
        )
        candidates.append(
            _SentenceMeaningCandidate(
                id=index,
                lemma=entry.lemma,
                meaning_key=normalize_token(entry.gloss or "") or entry.lemma,
                cor_lemma_idx=entry.lemma_idx,
                gloss=normalize_token(entry.gloss or "") or None,
                english_translation=english_translation,
                gloss_translation=gloss_translation,
                pos_tag=entry.pos_tag,
                morphology=entry.morphology,
                cor_id=entry.cor_id,
            )
        )
    return candidates


def _matching_surface_form_row(
    runtime: WordbankRuntime,
    *,
    lexeme_id: int,
    normalized_surface: str,
    meaning_id: int | None,
):
    rows = runtime.repository.find_surface_forms(lexeme_id=lexeme_id, form=normalized_surface)
    if not rows:
        return None
    if meaning_id is not None:
        scoped = next((row for row in rows if row.meaning_id == meaning_id), None)
        if scoped is not None:
            return scoped
    return rows[0]


def _sentence_token_card(token) -> SentenceTokenCard:
    return SentenceTokenCard(
        token_index=token.token_index,
        surface_form=token.surface_form,
        stored_lemma=token.stored_lemma,
        lexeme_id=token.lexeme_id,
        meaning_id=token.meaning_id,
        pos_tag=token.pos_tag,
        morphology=token.morphology,
        gloss=token.gloss,
        english_translation=token.english_translation,
        gloss_translation=token.gloss_translation,
    )


def _sentence_summary(row: SentenceRecord) -> SentenceSummary:
    return SentenceSummary(
        id=row.id,
        source_text=row.source_text,
        english_translation=row.english_translation,
        created_at=row.created_at,
        tokens=[_sentence_token_card(token) for token in row.tokens],
    )


def _sentence_response(
    row: SentenceRecord,
    *,
    status: Literal["inserted", "exists"],
    message: str,
) -> AddSentenceResponse:
    return AddSentenceResponse(
        id=row.id,
        source_text=row.source_text,
        english_translation=row.english_translation,
        created_at=row.created_at,
        tokens=[_sentence_token_card(token) for token in row.tokens],
        status=status,
        message=message,
    )
