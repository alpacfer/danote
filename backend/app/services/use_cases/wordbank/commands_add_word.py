from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.api.schemas.v1.wordbank import AddWordResponse
from app.services.gemini_translation import ContextualWordTranslationInput
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.collaborators.translation import TranslationLookupResult
from app.services.use_cases.wordbank.runtime import WordbankRuntime


@dataclass(frozen=True, slots=True)
class _AddWordInputs:
    normalized_surface: str
    stored_lemma: str
    normalized_cor_id: str | None
    selected_pos_tag: str | None
    selected_morphology: str | None


@dataclass(frozen=True, slots=True)
class _WordMetadata:
    translation: str | None
    provider: str | None
    pos_tag: str | None
    morphology: str | None


@dataclass(frozen=True, slots=True)
class _ContextualTranslationTarget:
    id: Literal["lemma", "surface"]
    surface_form: str
    lemma: str
    preferred_pos_tag: str | None
    preferred_morphology: str | None


@dataclass(frozen=True, slots=True)
class _TranslationSelection:
    lemma: TranslationLookupResult
    surface: TranslationLookupResult


@dataclass(frozen=True, slots=True)
class _AddWordWriteResult:
    inserted_lexeme: bool
    inserted_surface_form: bool
    inserted_lemma_surface_form: bool
    inserted_cor_variant: bool

    @property
    def inserted_any(self) -> bool:
        return (
            self.inserted_lexeme
            or self.inserted_surface_form
            or self.inserted_lemma_surface_form
            or self.inserted_cor_variant
        )


_NO_TRANSLATION = TranslationLookupResult(translation=None, provider=None)


def add_word(
    runtime: WordbankRuntime,
    surface_token: str,
    lemma_candidate: str | None,
    *,
    cor_id: str | None = None,
    pos_tag: str | None = None,
    morphology: str | None = None,
) -> AddWordResponse:
    inputs = _normalize_add_word_inputs(runtime, surface_token, lemma_candidate, cor_id, pos_tag, morphology)
    translations = _lookup_word_translations(runtime, inputs)
    lemma_metadata = _build_lemma_metadata(runtime, inputs, translations.lemma)
    surface_metadata = _build_surface_metadata(runtime, inputs, translations.surface)
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
    inserted_cor_variant = _sync_surface_form_cor_variant(
        runtime,
        lexeme_id=lexeme_id,
        inputs=inputs,
    )

    runtime.nlp.invalidate_pos_cache(inputs.stored_lemma, inputs.normalized_surface or None)
    write_result = _AddWordWriteResult(
        inserted_lexeme=inserted_lexeme,
        inserted_surface_form=inserted_surface_form,
        inserted_lemma_surface_form=inserted_lemma_surface_form,
        inserted_cor_variant=inserted_cor_variant,
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
    cor_id: str | None,
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
        normalized_cor_id=(cor_id or "").strip() or None,
        selected_pos_tag=runtime.nlp.normalize_optional_pos_tag(pos_tag),
        selected_morphology=runtime.nlp.normalize_optional_morphology(morphology),
    )


def _build_lemma_metadata(
    runtime: WordbankRuntime,
    inputs: _AddWordInputs,
    translation_result: TranslationLookupResult,
) -> _WordMetadata:
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


def _build_surface_metadata(
    runtime: WordbankRuntime,
    inputs: _AddWordInputs,
    translation_result: TranslationLookupResult,
) -> _WordMetadata:
    if not inputs.normalized_surface:
        return _WordMetadata(translation=None, provider=None, pos_tag=None, morphology=None)
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


def _sync_surface_form_cor_variant(
    runtime: WordbankRuntime,
    *,
    lexeme_id: int,
    inputs: _AddWordInputs,
) -> bool:
    if not inputs.normalized_cor_id:
        return False
    form = inputs.normalized_surface or inputs.stored_lemma
    return runtime.repository.insert_surface_form_cor_variant(
        lexeme_id=lexeme_id,
        form=form,
        cor_id=inputs.normalized_cor_id,
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


def _lookup_word_translations(
    runtime: WordbankRuntime,
    inputs: _AddWordInputs,
) -> _TranslationSelection:
    targets: list[_ContextualTranslationTarget] = [
        _ContextualTranslationTarget(
            id="lemma",
            surface_form=inputs.stored_lemma,
            lemma=inputs.stored_lemma,
            preferred_pos_tag=inputs.selected_pos_tag,
            preferred_morphology=inputs.selected_morphology,
        )
    ]
    if inputs.normalized_surface:
        targets.append(
            _ContextualTranslationTarget(
                id="surface",
                surface_form=inputs.normalized_surface,
                lemma=inputs.stored_lemma,
                preferred_pos_tag=inputs.selected_pos_tag,
                preferred_morphology=inputs.selected_morphology,
            )
        )

    contextual_results = _batch_lookup_contextual_translations(runtime, targets)
    resolved: dict[str, TranslationLookupResult] = {}
    for target in targets:
        contextual = contextual_results.get(target.id, _NO_TRANSLATION)
        resolved[target.id] = _resolve_translation_with_fallback(runtime, target, contextual)

    return _TranslationSelection(
        lemma=resolved.get("lemma", _NO_TRANSLATION),
        surface=resolved.get("surface", _NO_TRANSLATION),
    )


def _batch_lookup_contextual_translations(
    runtime: WordbankRuntime,
    targets: list[_ContextualTranslationTarget],
) -> dict[str, TranslationLookupResult]:
    if not targets:
        return {}

    payloads_by_key: dict[
        tuple[str, str, str | None, str | None, str | None, str | None, str | None],
        ContextualWordTranslationInput,
    ] = {}
    target_key_by_id: dict[str, tuple[str, str, str | None, str | None, str | None, str | None, str | None]] = {}
    for target in targets:
        payload = _build_contextual_payload(runtime, target)
        cache_key = runtime.translation.contextual_translation_cache_key(payload)
        target_key_by_id[target.id] = cache_key
        if cache_key not in payloads_by_key:
            payloads_by_key[cache_key] = payload

    payloads = list(payloads_by_key.values())
    contextual_results = runtime.translation.batch_lookup_contextual_word_translations(payloads)
    result_by_key: dict[
        tuple[str, str, str | None, str | None, str | None, str | None, str | None],
        TranslationLookupResult,
    ] = {}
    for key, result in zip(payloads_by_key.keys(), contextual_results, strict=False):
        result_by_key[key] = result

    by_target: dict[str, TranslationLookupResult] = {}
    for target_id, cache_key in target_key_by_id.items():
        by_target[target_id] = result_by_key.get(cache_key, _NO_TRANSLATION)
    return by_target


def _build_contextual_payload(
    runtime: WordbankRuntime,
    target: _ContextualTranslationTarget,
) -> ContextualWordTranslationInput:
    cor_entry = runtime.cor.best_cor_local_entry_for_form(
        form=target.surface_form,
        lemma=target.lemma,
        preferred_pos_tag=target.preferred_pos_tag,
    )
    if cor_entry is None:
        return ContextualWordTranslationInput(
            surface_form=target.surface_form,
            lemma=target.lemma,
            pos_tag=target.preferred_pos_tag,
            morphology=target.preferred_morphology,
            gloss=None,
        )
    return ContextualWordTranslationInput(
        surface_form=target.surface_form,
        lemma=target.lemma,
        pos_tag=target.preferred_pos_tag or cor_entry.pos_tag,
        morphology=target.preferred_morphology or cor_entry.morphology,
        gloss=normalize_token(cor_entry.gloss or "") or None,
    )


def _resolve_translation_with_fallback(
    runtime: WordbankRuntime,
    target: _ContextualTranslationTarget,
    contextual: TranslationLookupResult,
) -> TranslationLookupResult:
    if contextual.translation:
        return contextual

    translated = runtime.translation.lookup_translation(target.surface_form)
    if (
        translated
        and " " not in target.surface_form
        and runtime.translation.normalize_comparable(translated)
        == runtime.translation.normalize_comparable(target.surface_form)
    ):
        return _NO_TRANSLATION
    return TranslationLookupResult(
        translation=translated,
        provider=runtime.translation.provider_name() if translated else None,
    )
