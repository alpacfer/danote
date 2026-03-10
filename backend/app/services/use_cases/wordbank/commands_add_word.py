from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal

from app.api.schemas.v1.wordbank import AddWordResponse
from app.services.cor_local import CORLocalEntry
from app.services.gemini_translation import ContextualWordTranslationInput
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.collaborators.cor_azure_frames import (
    azure_framed_translation_for_comparison,
    cor_local_azure_frame,
)
from app.services.use_cases.wordbank.collaborators.cor_local_translations import (
    lookup_translation_for_cor_local_entry,
)
from app.services.use_cases.wordbank.collaborators.translation import TranslationLookupResult
from app.services.use_cases.wordbank.commands_add_word_search_seed import add_word_from_search_seed
from app.services.use_cases.wordbank.meaning_sections import (
    MeaningResolution,
    build_meaning_assignment,
    ensure_wordbank_meaning_compatibility,
    resolve_meaning_translation,
    resolve_non_verb_meaning,
)
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
    id: Literal["lemma"]
    surface_form: str
    lemma: str
    preferred_pos_tag: str | None
    preferred_morphology: str | None
    cor_entry: CORLocalEntry | None


@dataclass(frozen=True, slots=True)
class _TranslationSelection:
    lemma: TranslationLookupResult


@dataclass(frozen=True, slots=True)
class _AddWordWriteResult:
    inserted_lexeme: bool
    inserted_meaning: bool
    inserted_surface_form: bool
    inserted_lemma_surface_form: bool
    inserted_cor_variant: bool

    @property
    def inserted_any(self) -> bool:
        return (
            self.inserted_lexeme
            or self.inserted_meaning
            or self.inserted_surface_form
            or self.inserted_lemma_surface_form
            or self.inserted_cor_variant
        )


_NO_TRANSLATION = TranslationLookupResult(translation=None, provider=None)
_LIKELY_ENGLISH_GLOSS_RE = re.compile(r"^[A-Za-z][A-Za-z ',-]*$")


def add_word(
    runtime: WordbankRuntime,
    surface_token: str,
    lemma_candidate: str | None,
    *,
    cor_id: str | None = None,
    pos_tag: str | None = None,
    morphology: str | None = None,
    search_seed: dict[str, object] | None = None,
) -> AddWordResponse:
    if search_seed is not None:
        return add_word_from_search_seed(
            runtime,
            surface_token=surface_token,
            lemma_candidate=lemma_candidate,
            search_seed=search_seed,
        )
    ensure_wordbank_meaning_compatibility(runtime)
    inputs = _normalize_add_word_inputs(runtime, surface_token, lemma_candidate, cor_id, pos_tag, morphology)
    initial_metadata = _extract_root_metadata(runtime, inputs)
    lexeme_id, inserted_lexeme = runtime.repository.insert_or_load_lexeme(
        stored_lemma=inputs.stored_lemma,
        translation=None,
        provider=None,
        pos_tag=initial_metadata.pos_tag,
        morphology=initial_metadata.morphology,
    )

    meaning_resolution = resolve_non_verb_meaning(
        runtime,
        lexeme_id=lexeme_id,
        stored_lemma=inputs.stored_lemma,
        normalized_surface=inputs.normalized_surface,
        normalized_cor_id=inputs.normalized_cor_id,
        preferred_pos_tag=initial_metadata.pos_tag,
        preferred_morphology=initial_metadata.morphology,
    )
    translations = _lookup_word_translations(runtime, inputs, meaning_resolution)

    if meaning_resolution is None:
        return _add_unsectioned_word(
            runtime,
            inputs=inputs,
            lexeme_id=lexeme_id,
            inserted_lexeme=inserted_lexeme,
            initial_metadata=initial_metadata,
            translations=translations,
        )
    return _add_meaning_scoped_word(
        runtime,
        inputs=inputs,
        lexeme_id=lexeme_id,
        inserted_lexeme=inserted_lexeme,
        meaning_resolution=meaning_resolution,
        translations=translations,
    )


def _add_meaning_scoped_word(
    runtime: WordbankRuntime,
    *,
    inputs: _AddWordInputs,
    lexeme_id: int,
    inserted_lexeme: bool,
    meaning_resolution: MeaningResolution,
    translations: _TranslationSelection,
) -> AddWordResponse:
    meaning_translation = resolve_meaning_translation(
        runtime,
        cor_entry=meaning_resolution.lemma_cor_entry or meaning_resolution.surface_cor_entry,
        gloss=meaning_resolution.gloss,
        lemma_translation=translations.lemma.translation,
    )
    meaning_record, inserted_meaning = runtime.repository.upsert_lexeme_meaning(
        lexeme_id=lexeme_id,
        meaning_key=(
            meaning_resolution.selected.meaning_key
            if meaning_resolution.selected is not None
            else meaning_resolution.meaning_key
        ),
        cor_lemma_idx=meaning_resolution.cor_lemma_idx,
        gloss=meaning_resolution.gloss,
        english_translation=meaning_translation,
        pos_tag=meaning_resolution.pos_tag,
        morphology=meaning_resolution.morphology,
    )
    lemma_metadata = _build_meaning_scoped_metadata(
        runtime,
        form=inputs.stored_lemma,
        preferred_pos_tag=meaning_resolution.pos_tag,
        preferred_morphology=meaning_resolution.morphology,
        translation_result=translations.lemma,
        cor_entry=meaning_resolution.lemma_cor_entry or meaning_resolution.surface_cor_entry,
    )
    actual_surface = inputs.normalized_surface or inputs.stored_lemma
    surface_metadata = _build_meaning_scoped_metadata(
        runtime,
        form=actual_surface,
        preferred_pos_tag=meaning_resolution.surface_cor_entry.pos_tag
        if meaning_resolution.surface_cor_entry is not None
        else meaning_resolution.pos_tag,
        preferred_morphology=meaning_resolution.surface_cor_entry.morphology
        if meaning_resolution.surface_cor_entry is not None
        else meaning_resolution.morphology,
        translation_result=_NO_TRANSLATION,
        cor_entry=meaning_resolution.surface_cor_entry or meaning_resolution.lemma_cor_entry,
    )

    inserted_lemma_surface_form = False
    if actual_surface == inputs.stored_lemma:
        actual_surface_form, inserted_surface_form = runtime.repository.insert_or_update_surface_form(
            lexeme_id=lexeme_id,
            meaning_id=meaning_record.id,
            form=actual_surface,
            pos_tag=surface_metadata.pos_tag or lemma_metadata.pos_tag,
            morphology=surface_metadata.morphology or lemma_metadata.morphology,
        )
    else:
        lemma_surface_form, inserted_lemma_surface_form = runtime.repository.insert_or_update_surface_form(
            lexeme_id=lexeme_id,
            meaning_id=meaning_record.id,
            form=inputs.stored_lemma,
            pos_tag=lemma_metadata.pos_tag,
            morphology=lemma_metadata.morphology,
        )
        actual_surface_form, inserted_surface_form = runtime.repository.insert_or_update_surface_form(
            lexeme_id=lexeme_id,
            meaning_id=meaning_record.id,
            form=actual_surface,
            pos_tag=surface_metadata.pos_tag or lemma_metadata.pos_tag,
            morphology=surface_metadata.morphology or lemma_metadata.morphology,
        )
        del lemma_surface_form

    inserted_cor_variant = _sync_surface_form_cor_variant(
        runtime,
        surface_form_id=actual_surface_form.id,
        normalized_cor_id=inputs.normalized_cor_id,
    )

    runtime.nlp.invalidate_pos_cache(inputs.stored_lemma, inputs.normalized_surface or None)
    write_result = _AddWordWriteResult(
        inserted_lexeme=inserted_lexeme,
        inserted_meaning=inserted_meaning,
        inserted_surface_form=inserted_surface_form,
        inserted_lemma_surface_form=inserted_lemma_surface_form,
        inserted_cor_variant=inserted_cor_variant,
    )
    if write_result.inserted_any:
        runtime.nlp.add_user_lexeme(inputs.stored_lemma)
    meaning_assignment = build_meaning_assignment(meaning_record)
    return _build_add_word_response(
        inputs=inputs,
        write_result=write_result,
        meaning=meaning_assignment,
        verification=runtime.verification.queued_verification_result(),
    )


def _add_unsectioned_word(
    runtime: WordbankRuntime,
    *,
    inputs: _AddWordInputs,
    lexeme_id: int,
    inserted_lexeme: bool,
    initial_metadata: _WordMetadata,
    translations: _TranslationSelection,
) -> AddWordResponse:
    lemma_metadata = _build_root_metadata(runtime, inputs, translations.lemma, initial_metadata)
    surface_metadata = _build_surface_metadata(runtime, inputs)
    runtime.repository.insert_or_load_lexeme(
        stored_lemma=inputs.stored_lemma,
        translation=lemma_metadata.translation,
        provider=lemma_metadata.provider,
        pos_tag=lemma_metadata.pos_tag,
        morphology=lemma_metadata.morphology,
    )

    inserted_lemma_surface_form = False
    actual_surface = inputs.normalized_surface or inputs.stored_lemma
    if actual_surface == inputs.stored_lemma:
        surface_form, inserted_surface_form = runtime.repository.insert_or_update_surface_form(
            lexeme_id=lexeme_id,
            meaning_id=None,
            form=actual_surface,
            pos_tag=surface_metadata.pos_tag or lemma_metadata.pos_tag,
            morphology=surface_metadata.morphology or lemma_metadata.morphology,
        )
    else:
        _lemma_surface_form, inserted_lemma_surface_form = runtime.repository.insert_or_update_surface_form(
            lexeme_id=lexeme_id,
            meaning_id=None,
            form=inputs.stored_lemma,
            pos_tag=lemma_metadata.pos_tag,
            morphology=lemma_metadata.morphology,
        )
        surface_form, inserted_surface_form = runtime.repository.insert_or_update_surface_form(
            lexeme_id=lexeme_id,
            meaning_id=None,
            form=actual_surface,
            pos_tag=surface_metadata.pos_tag,
            morphology=surface_metadata.morphology,
        )

    inserted_cor_variant = _sync_surface_form_cor_variant(
        runtime,
        surface_form_id=surface_form.id,
        normalized_cor_id=inputs.normalized_cor_id,
    )
    runtime.nlp.invalidate_pos_cache(inputs.stored_lemma, inputs.normalized_surface or None)
    write_result = _AddWordWriteResult(
        inserted_lexeme=inserted_lexeme,
        inserted_meaning=False,
        inserted_surface_form=inserted_surface_form,
        inserted_lemma_surface_form=inserted_lemma_surface_form,
        inserted_cor_variant=inserted_cor_variant,
    )
    if write_result.inserted_any:
        runtime.nlp.add_user_lexeme(inputs.stored_lemma)
    return _build_add_word_response(
        inputs=inputs,
        write_result=write_result,
        meaning=None,
        verification=runtime.verification.queued_verification_result(),
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


def _extract_root_metadata(runtime: WordbankRuntime, inputs: _AddWordInputs) -> _WordMetadata:
    pos_tag, morphology = runtime.nlp.extract_pos_and_morphology(
        inputs.stored_lemma,
        preferred_pos_tag=inputs.selected_pos_tag,
    )
    if pos_tag is None:
        pos_tag = inputs.selected_pos_tag
    if morphology is None:
        morphology = inputs.selected_morphology
    return _WordMetadata(
        translation=None,
        provider=None,
        pos_tag=pos_tag,
        morphology=morphology,
    )


def _build_root_metadata(
    runtime: WordbankRuntime,
    inputs: _AddWordInputs,
    translation_result: TranslationLookupResult,
    initial_metadata: _WordMetadata,
) -> _WordMetadata:
    pos_tag = initial_metadata.pos_tag
    morphology = initial_metadata.morphology
    if pos_tag is None or morphology is None:
        pos_tag, morphology = runtime.nlp.extract_pos_and_morphology(
            inputs.stored_lemma,
            preferred_pos_tag=inputs.selected_pos_tag,
        )
    return _WordMetadata(
        translation=translation_result.translation,
        provider=translation_result.provider,
        pos_tag=pos_tag or inputs.selected_pos_tag,
        morphology=morphology or inputs.selected_morphology,
    )


def _build_surface_metadata(
    runtime: WordbankRuntime,
    inputs: _AddWordInputs,
) -> _WordMetadata:
    actual_surface = inputs.normalized_surface or inputs.stored_lemma
    if inputs.selected_pos_tag is not None or inputs.selected_morphology is not None:
        return _WordMetadata(
            translation=None,
            provider=None,
            pos_tag=inputs.selected_pos_tag,
            morphology=inputs.selected_morphology,
        )
    pos_tag, morphology = runtime.nlp.extract_pos_and_morphology(
        actual_surface,
        preferred_pos_tag=inputs.selected_pos_tag,
    )
    return _WordMetadata(
        translation=None,
        provider=None,
        pos_tag=pos_tag,
        morphology=morphology,
    )


def _build_meaning_scoped_metadata(
    runtime: WordbankRuntime,
    *,
    form: str,
    preferred_pos_tag: str | None,
    preferred_morphology: str | None,
    translation_result: TranslationLookupResult,
    cor_entry: CORLocalEntry | None,
) -> _WordMetadata:
    pos_tag = preferred_pos_tag or (cor_entry.pos_tag if cor_entry is not None else None)
    morphology = preferred_morphology or (cor_entry.morphology if cor_entry is not None else None)
    if pos_tag is None or morphology is None:
        extracted_pos_tag, extracted_morphology = runtime.nlp.extract_pos_and_morphology(
            form,
            preferred_pos_tag=preferred_pos_tag,
        )
        pos_tag = pos_tag or extracted_pos_tag
        morphology = morphology or extracted_morphology
    return _WordMetadata(
        translation=translation_result.translation,
        provider=translation_result.provider,
        pos_tag=pos_tag,
        morphology=morphology,
    )


def _sync_surface_form_cor_variant(
    runtime: WordbankRuntime,
    *,
    surface_form_id: int,
    normalized_cor_id: str | None,
) -> bool:
    if not normalized_cor_id:
        return False
    return runtime.repository.insert_surface_form_cor_variant(
        surface_form_id=surface_form_id,
        cor_id=normalized_cor_id,
    )


def _lookup_word_translations(
    runtime: WordbankRuntime,
    inputs: _AddWordInputs,
    meaning_resolution: MeaningResolution | None,
) -> _TranslationSelection:
    lemma_cor_entry = None
    prefer_cor_lemma_translation = False
    preferred_pos_tag = inputs.selected_pos_tag
    preferred_morphology = inputs.selected_morphology
    if meaning_resolution is not None:
        lemma_cor_entry = meaning_resolution.lemma_cor_entry or meaning_resolution.surface_cor_entry
        prefer_cor_lemma_translation = meaning_resolution.lemma_cor_entry is not None or (
            meaning_resolution.surface_cor_entry is not None
            and normalize_token(meaning_resolution.surface_cor_entry.form) == inputs.stored_lemma
        )
        preferred_pos_tag = meaning_resolution.pos_tag
        preferred_morphology = meaning_resolution.morphology
    elif inputs.normalized_cor_id:
        surface_cor_entry = runtime.cor.cor_local_entry_for_cor_id(cor_id=inputs.normalized_cor_id)
        if surface_cor_entry is not None and normalize_token(surface_cor_entry.lemma) == inputs.stored_lemma:
            lemma_cor_entry = runtime.cor.best_cor_local_lemma_entry(
                lemma_idx=surface_cor_entry.lemma_idx,
                lemma=inputs.stored_lemma,
                preferred_pos_tag=surface_cor_entry.pos_tag or inputs.selected_pos_tag,
            )
            prefer_cor_lemma_translation = lemma_cor_entry is not None
            preferred_pos_tag = surface_cor_entry.pos_tag or inputs.selected_pos_tag
            preferred_morphology = surface_cor_entry.morphology or inputs.selected_morphology

    targets: list[_ContextualTranslationTarget] = [
        _ContextualTranslationTarget(
            id="lemma",
            surface_form=inputs.stored_lemma,
            lemma=inputs.stored_lemma,
            preferred_pos_tag=preferred_pos_tag,
            preferred_morphology=preferred_morphology,
            cor_entry=lemma_cor_entry,
        )
    ]
    contextual_results = _batch_lookup_contextual_translations(runtime, targets)
    resolved: dict[str, TranslationLookupResult] = {}
    for target in targets:
        if target.id == "lemma" and prefer_cor_lemma_translation and lemma_cor_entry is not None:
            resolved[target.id] = _resolve_cor_lemma_translation(
                runtime,
                cor_entry=lemma_cor_entry,
            )
            continue
        contextual = contextual_results.get(target.id, _NO_TRANSLATION)
        resolved[target.id] = _resolve_translation_with_fallback(runtime, target, contextual)

    return _TranslationSelection(
        lemma=resolved.get("lemma", _NO_TRANSLATION),
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

    return {
        target_id: result_by_key.get(cache_key, _NO_TRANSLATION)
        for target_id, cache_key in target_key_by_id.items()
    }


def _build_contextual_payload(
    runtime: WordbankRuntime,
    target: _ContextualTranslationTarget,
) -> ContextualWordTranslationInput:
    cor_entry = target.cor_entry
    if cor_entry is None:
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


def _resolve_cor_lemma_translation(
    runtime: WordbankRuntime,
    *,
    cor_entry: CORLocalEntry,
) -> TranslationLookupResult:
    frame = cor_local_azure_frame(cor_entry)
    framed_translation = azure_framed_translation_for_comparison(
        frame,
        runtime.translation.lookup_translation(frame.text),
    )
    if framed_translation and _is_likely_english_gloss(cor_entry.gloss):
        return TranslationLookupResult(
            translation=framed_translation,
            provider=runtime.translation.provider_name(),
        )

    translated = lookup_translation_for_cor_local_entry(
        runtime.translation,
        cor_entry,
    )
    return TranslationLookupResult(
        translation=translated,
        provider=runtime.translation.provider_name() if translated else None,
    )


def _is_likely_english_gloss(gloss: str | None) -> bool:
    normalized_gloss = normalize_token(gloss or "")
    if not normalized_gloss:
        return False
    return _LIKELY_ENGLISH_GLOSS_RE.fullmatch(normalized_gloss) is not None


def _build_add_word_response(
    *,
    inputs: _AddWordInputs,
    write_result: _AddWordWriteResult,
    meaning,
    verification: AddWordResponse.VerificationResult | None,
) -> AddWordResponse:
    status: Literal["inserted", "exists"] = "inserted" if write_result.inserted_any else "exists"
    message = (
        f"Added '{inputs.stored_lemma}' to wordbank."
        if write_result.inserted_any
        else f"'{inputs.stored_lemma}' is already in the wordbank."
    )
    return AddWordResponse(
        status=status,
        stored_lemma=inputs.stored_lemma,
        stored_surface_form=inputs.normalized_surface or None,
        source="manual",
        message=message,
        meaning=(
            AddWordResponse.MeaningContext(
                id=meaning.id,
                meaning_key=meaning.meaning_key,
                gloss=meaning.gloss,
                english_translation=meaning.english_translation,
            )
            if meaning is not None
            else None
        ),
        verification=verification,
    )
