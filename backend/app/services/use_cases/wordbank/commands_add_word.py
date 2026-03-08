from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.api.schemas.v1.wordbank import AddWordResponse
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.runtime import WordbankRuntime


@dataclass(frozen=True, slots=True)
class _AddWordInputs:
    normalized_surface: str
    stored_lemma: str
    selected_pos_tag: str | None
    selected_morphology: str | None


@dataclass(frozen=True, slots=True)
class _WordMetadata:
    translation: str | None
    provider: str | None
    pos_tag: str | None
    morphology: str | None


@dataclass(frozen=True, slots=True)
class _AddWordWriteResult:
    inserted_lexeme: bool
    inserted_surface_form: bool
    inserted_lemma_surface_form: bool

    @property
    def inserted_any(self) -> bool:
        return self.inserted_lexeme or self.inserted_surface_form or self.inserted_lemma_surface_form


def add_word(
    runtime: WordbankRuntime,
    surface_token: str,
    lemma_candidate: str | None,
    *,
    pos_tag: str | None = None,
    morphology: str | None = None,
) -> AddWordResponse:
    inputs = _normalize_add_word_inputs(runtime, surface_token, lemma_candidate, pos_tag, morphology)
    lemma_metadata = _build_lemma_metadata(runtime, inputs)
    surface_metadata = _build_surface_metadata(runtime, inputs)
    lexeme_id, inserted_lexeme = runtime.repository.insert_or_load_lexeme(
        stored_lemma=inputs.stored_lemma,
        translation=lemma_metadata.translation,
        provider=lemma_metadata.provider,
        pos_tag=lemma_metadata.pos_tag,
        morphology=lemma_metadata.morphology,
    )
    inserted_lemma_surface_form = _sync_lemma_surface_form(
        runtime,
        lexeme_id=lexeme_id,
        inputs=inputs,
        metadata=lemma_metadata,
        provider=lemma_metadata.provider,
    )
    inserted_surface_form = _sync_surface_form(
        runtime,
        lexeme_id=lexeme_id,
        inputs=inputs,
        metadata=surface_metadata,
        provider=surface_metadata.provider,
    )

    runtime.nlp.invalidate_pos_cache(inputs.stored_lemma, inputs.normalized_surface or None)
    write_result = _AddWordWriteResult(
        inserted_lexeme=inserted_lexeme,
        inserted_surface_form=inserted_surface_form,
        inserted_lemma_surface_form=inserted_lemma_surface_form,
    )
    if write_result.inserted_any:
        runtime.nlp.add_user_lexeme(inputs.stored_lemma)

    status: Literal["inserted", "exists"] = "inserted" if write_result.inserted_any else "exists"
    message = (
        f"Added '{inputs.stored_lemma}' to wordbank."
        if write_result.inserted_any
        else f"'{inputs.stored_lemma}' is already in the wordbank."
    )
    verification = runtime.verification.queued_verification_result()
    return AddWordResponse(
        status=status,
        stored_lemma=inputs.stored_lemma,
        stored_surface_form=inputs.normalized_surface or None,
        source="manual",
        message=message,
        verification=verification,
    )


def _normalize_add_word_inputs(
    runtime: WordbankRuntime,
    surface_token: str,
    lemma_candidate: str | None,
    pos_tag: str | None,
    morphology: str | None,
) -> _AddWordInputs:
    normalized_surface = normalize_token(surface_token)
    normalized_lemma = normalize_token(lemma_candidate or "")
    stored_lemma = normalized_lemma or normalized_surface
    if not stored_lemma:
        raise ValueError("surface_token or lemma_candidate is required")
    return _AddWordInputs(
        normalized_surface=normalized_surface,
        stored_lemma=stored_lemma,
        selected_pos_tag=runtime.nlp.normalize_optional_pos_tag(pos_tag),
        selected_morphology=runtime.nlp.normalize_optional_morphology(morphology),
    )


def _build_lemma_metadata(runtime: WordbankRuntime, inputs: _AddWordInputs) -> _WordMetadata:
    translation_result = runtime.translation.lookup_word_translation(inputs.stored_lemma, inputs.stored_lemma)
    pos_tag, morphology = runtime.nlp.extract_pos_and_morphology(
        inputs.stored_lemma,
        preferred_pos_tag=inputs.selected_pos_tag,
    )
    if pos_tag is None and inputs.selected_pos_tag is not None:
        pos_tag = inputs.selected_pos_tag
    if morphology is None and inputs.selected_morphology is not None:
        morphology = inputs.selected_morphology
    return _WordMetadata(
        translation=translation_result.translation,
        provider=translation_result.provider,
        pos_tag=pos_tag,
        morphology=morphology,
    )


def _build_surface_metadata(runtime: WordbankRuntime, inputs: _AddWordInputs) -> _WordMetadata:
    if not inputs.normalized_surface:
        return _WordMetadata(translation=None, provider=None, pos_tag=None, morphology=None)
    translation_result = runtime.translation.lookup_word_translation(
        inputs.normalized_surface,
        inputs.stored_lemma,
    )
    if inputs.selected_pos_tag is not None or inputs.selected_morphology is not None:
        return _WordMetadata(
            translation=translation_result.translation,
            provider=translation_result.provider,
            pos_tag=inputs.selected_pos_tag,
            morphology=inputs.selected_morphology,
        )
    pos_tag, morphology = runtime.nlp.extract_pos_and_morphology(
        inputs.normalized_surface,
        preferred_pos_tag=inputs.selected_pos_tag,
    )
    return _WordMetadata(
        translation=translation_result.translation,
        provider=translation_result.provider,
        pos_tag=pos_tag,
        morphology=morphology,
    )


def _sync_lemma_surface_form(
    runtime: WordbankRuntime,
    *,
    lexeme_id: int,
    inputs: _AddWordInputs,
    metadata: _WordMetadata,
    provider: str | None,
) -> bool:
    if not inputs.normalized_surface or inputs.normalized_surface == inputs.stored_lemma:
        return False
    return _insert_or_update_surface_form(
        runtime,
        lexeme_id=lexeme_id,
        form=inputs.stored_lemma,
        metadata=metadata,
        provider=provider,
    )


def _sync_surface_form(
    runtime: WordbankRuntime,
    *,
    lexeme_id: int,
    inputs: _AddWordInputs,
    metadata: _WordMetadata,
    provider: str | None,
) -> bool:
    if not inputs.normalized_surface:
        return False
    return _insert_or_update_surface_form(
        runtime,
        lexeme_id=lexeme_id,
        form=inputs.normalized_surface,
        metadata=metadata,
        provider=provider,
    )


def _insert_or_update_surface_form(
    runtime: WordbankRuntime,
    *,
    lexeme_id: int,
    form: str,
    metadata: _WordMetadata,
    provider: str | None,
) -> bool:
    return runtime.repository.insert_or_update_surface_form(
        lexeme_id=lexeme_id,
        form=form,
        translation=metadata.translation,
        provider=provider,
        pos_tag=metadata.pos_tag,
        morphology=metadata.morphology,
    )
