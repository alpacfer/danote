from __future__ import annotations

from app.api.schemas.v1.wordbank import AddWordResponse, MeaningContext, VerificationResult
from app.services.cor_local import CORLocalEntry
from app.services.gemini_translation import NonCORWordGenerationInput
from app.services.use_cases.wordbank.add_word_normalization import (
    normalize_add_word_inputs,
)
from app.services.use_cases.wordbank.collaborators.translation import TranslationLookupResult
from app.services.use_cases.wordbank.commands_add_word_models import (
    AddWordCommandInputs,
    AddWordWriteResult,
    WordMetadata,
)
from app.services.use_cases.wordbank.commands_add_word_response import (
    build_add_word_response,
)
from app.services.use_cases.wordbank.commands_add_word_search_seed import add_word_from_search_seed
from app.services.use_cases.wordbank.commands_add_word_translations import (
    NO_TRANSLATION,
    TranslationSelection,
    lookup_word_translations,
)
from app.services.use_cases.wordbank.meaning_sections import (
    MeaningResolution,
    build_meaning_assignment,
    ensure_wordbank_meaning_compatibility,
    resolve_meaning_translation,
    resolve_non_verb_meaning,
)
from app.services.use_cases.wordbank.non_cor_generation import build_non_cor_search_seed
from app.services.use_cases.wordbank.pronunciation_queue import queue_pronunciation_generation
from app.services.use_cases.wordbank.related_words_queue import queue_related_words_resolution
from app.services.use_cases.wordbank.runtime import WordbankRuntime
from app.services.use_cases.wordbank.verification_targets import (
    discover_word_page_verification_targets,
    queue_verification_targets,
)


def add_word(
    runtime: WordbankRuntime,
    surface_token: str,
    lemma_candidate: str | None,
    *,
    cor_id: str | None = None,
    pos_tag: str | None = None,
    morphology: str | None = None,
    search_seed: dict[str, object] | None = None,
    queue_verification: bool = True,
) -> AddWordResponse:
    if search_seed is not None:
        return add_word_from_search_seed(
            runtime,
            surface_token=surface_token,
            lemma_candidate=lemma_candidate,
            search_seed=search_seed,
            queue_verification=queue_verification,
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
        dictionary_status="cor" if inputs.normalized_cor_id else "unknown",
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
    if meaning_resolution is not None and _should_try_non_cor_generation(meaning_resolution):
        generated = _generate_non_cor_word(runtime, inputs=inputs)
        if generated is not None:
            return add_word_from_search_seed(
                runtime,
                surface_token=inputs.normalized_surface,
                lemma_candidate=generated.lemma,
                search_seed=build_non_cor_search_seed(
                    surface_form=inputs.normalized_surface,
                    generated=generated,
                ),
                queue_verification=queue_verification,
            )
    if meaning_resolution is None:
        translations = lookup_word_translations(runtime, inputs, meaning_resolution)
        return _add_unsectioned_word(
            runtime,
            inputs=inputs,
            lexeme_id=lexeme_id,
            inserted_lexeme=inserted_lexeme,
            initial_metadata=initial_metadata,
            translations=translations,
        )
    translations = lookup_word_translations(runtime, inputs, meaning_resolution)
    return _add_meaning_scoped_word(
        runtime,
        inputs=inputs,
        lexeme_id=lexeme_id,
        inserted_lexeme=inserted_lexeme,
        meaning_resolution=meaning_resolution,
        translations=translations,
    )


def _should_try_non_cor_generation(meaning_resolution: MeaningResolution) -> bool:
    resolved_pos_tag = (meaning_resolution.pos_tag or "").upper()
    if resolved_pos_tag and resolved_pos_tag not in {"ADJ", "NOUN", "PROPN"}:
        return False
    return (
        meaning_resolution.selected is None
        and meaning_resolution.surface_cor_entry is None
        and meaning_resolution.lemma_cor_entry is None
        and meaning_resolution.cor_lemma_idx is None
    )


def _add_meaning_scoped_word(
    runtime: WordbankRuntime,
    *,
    inputs: AddWordCommandInputs,
    lexeme_id: int,
    inserted_lexeme: bool,
    meaning_resolution: MeaningResolution,
    translations: TranslationSelection,
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
        dictionary_status="cor",
        gloss=meaning_resolution.gloss,
        english_translation=meaning_translation,
        pos_tag=meaning_resolution.pos_tag,
        morphology=meaning_resolution.morphology,
    )
    runtime.repository.insert_or_load_lexeme(
        stored_lemma=inputs.stored_lemma,
        translation=None,
        provider=None,
        pos_tag=meaning_resolution.pos_tag,
        morphology=meaning_resolution.morphology,
        source="manual",
        dictionary_status="cor",
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
        translation_result=NO_TRANSLATION,
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
    write_result = AddWordWriteResult(
        inserted_lexeme=inserted_lexeme,
        inserted_meaning=inserted_meaning,
        inserted_surface_form=inserted_surface_form,
        inserted_lemma_surface_form=inserted_lemma_surface_form,
        inserted_cor_variant=inserted_cor_variant,
    )
    if write_result.inserted_any:
        runtime.nlp.add_user_lexeme(inputs.stored_lemma)
    meaning_assignment = build_meaning_assignment(meaning_record)
    verification = runtime.verification.queued_verification_result(
        stored_surface_form=inputs.normalized_surface or inputs.stored_lemma,
    )
    queued_verification_targets = queue_verification_targets(
        runtime,
        stored_lemma=inputs.stored_lemma,
        targets=discover_word_page_verification_targets(
            runtime,
            stored_lemma=inputs.stored_lemma,
        ),
    )
    queued_pronunciation_forms = queue_pronunciation_generation(
        runtime,
        stored_lemma=inputs.stored_lemma,
        requested_forms=(actual_surface,),
    )
    queue_related_words_resolution(
        runtime,
        stored_lemma=inputs.stored_lemma,
    )
    return build_add_word_response(
        runtime=runtime,
        inputs=inputs,
        write_result=write_result,
        meaning=meaning_assignment,
        verification=verification,
        queued_verification_targets=queued_verification_targets,
        queued_pronunciation_forms=queued_pronunciation_forms,
        pronunciation=runtime.pronunciation.queued_pronunciation_result(
            inputs.stored_lemma,
            actual_surface,
        ),
    )


def _add_unsectioned_word(
    runtime: WordbankRuntime,
    *,
    inputs: AddWordCommandInputs,
    lexeme_id: int,
    inserted_lexeme: bool,
    initial_metadata: WordMetadata,
    translations: TranslationSelection,
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
    write_result = AddWordWriteResult(
        inserted_lexeme=inserted_lexeme,
        inserted_meaning=False,
        inserted_surface_form=inserted_surface_form,
        inserted_lemma_surface_form=inserted_lemma_surface_form,
        inserted_cor_variant=inserted_cor_variant,
    )
    if write_result.inserted_any:
        runtime.nlp.add_user_lexeme(inputs.stored_lemma)
    verification = runtime.verification.queued_verification_result(
        stored_surface_form=inputs.normalized_surface or inputs.stored_lemma,
    )
    queued_verification_targets = queue_verification_targets(
        runtime,
        stored_lemma=inputs.stored_lemma,
        targets=discover_word_page_verification_targets(
            runtime,
            stored_lemma=inputs.stored_lemma,
        ),
    )
    queued_pronunciation_forms = queue_pronunciation_generation(
        runtime,
        stored_lemma=inputs.stored_lemma,
        requested_forms=(actual_surface,),
    )
    queue_related_words_resolution(
        runtime,
        stored_lemma=inputs.stored_lemma,
    )
    return build_add_word_response(
        runtime=runtime,
        inputs=inputs,
        write_result=write_result,
        meaning=None,
        verification=verification,
        queued_verification_targets=queued_verification_targets,
        queued_pronunciation_forms=queued_pronunciation_forms,
        pronunciation=runtime.pronunciation.queued_pronunciation_result(
            inputs.stored_lemma,
            actual_surface,
        ),
    )


def _normalize_add_word_inputs(
    runtime: WordbankRuntime,
    surface_token: str,
    lemma_candidate: str | None,
    cor_id: str | None,
    pos_tag: str | None,
    morphology: str | None,
) -> AddWordCommandInputs:
    normalized = normalize_add_word_inputs(
        surface_token,
        lemma_candidate,
        cor_id,
        runtime.nlp.normalize_optional_pos_tag(pos_tag),
        runtime.nlp.normalize_optional_morphology(morphology),
    )
    return AddWordCommandInputs(
        normalized_surface=normalized.normalized_surface,
        stored_lemma=normalized.stored_lemma,
        normalized_cor_id=normalized.normalized_cor_id,
        selected_pos_tag=normalized.selected_pos_tag,
        selected_morphology=normalized.selected_morphology,
    )


def _extract_root_metadata(runtime: WordbankRuntime, inputs: AddWordCommandInputs) -> WordMetadata:
    pos_tag, morphology = runtime.nlp.extract_pos_and_morphology(
        inputs.stored_lemma,
        preferred_pos_tag=inputs.selected_pos_tag,
    )
    if pos_tag is None:
        pos_tag = inputs.selected_pos_tag
    if morphology is None:
        morphology = inputs.selected_morphology
    return WordMetadata(
        translation=None,
        provider=None,
        pos_tag=pos_tag,
        morphology=morphology,
    )


def _build_root_metadata(
    runtime: WordbankRuntime,
    inputs: AddWordCommandInputs,
    translation_result: TranslationLookupResult,
    initial_metadata: WordMetadata,
) -> WordMetadata:
    pos_tag = initial_metadata.pos_tag
    morphology = initial_metadata.morphology
    if pos_tag is None or morphology is None:
        pos_tag, morphology = runtime.nlp.extract_pos_and_morphology(
            inputs.stored_lemma,
            preferred_pos_tag=inputs.selected_pos_tag,
        )
    return WordMetadata(
        translation=translation_result.translation,
        provider=translation_result.provider,
        pos_tag=pos_tag or inputs.selected_pos_tag,
        morphology=morphology or inputs.selected_morphology,
    )


def _build_surface_metadata(
    runtime: WordbankRuntime,
    inputs: AddWordCommandInputs,
) -> WordMetadata:
    actual_surface = inputs.normalized_surface or inputs.stored_lemma
    if inputs.selected_pos_tag is not None or inputs.selected_morphology is not None:
        return WordMetadata(
            translation=None,
            provider=None,
            pos_tag=inputs.selected_pos_tag,
            morphology=inputs.selected_morphology,
        )
    pos_tag, morphology = runtime.nlp.extract_pos_and_morphology(
        actual_surface,
        preferred_pos_tag=inputs.selected_pos_tag,
    )
    return WordMetadata(
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
) -> WordMetadata:
    pos_tag = preferred_pos_tag or (cor_entry.pos_tag if cor_entry is not None else None)
    morphology = preferred_morphology or (cor_entry.morphology if cor_entry is not None else None)
    if pos_tag is None or morphology is None:
        extracted_pos_tag, extracted_morphology = runtime.nlp.extract_pos_and_morphology(
            form,
            preferred_pos_tag=preferred_pos_tag,
        )
        pos_tag = pos_tag or extracted_pos_tag
        morphology = morphology or extracted_morphology
    return WordMetadata(
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


def _generate_non_cor_word(
    runtime: WordbankRuntime,
    *,
    inputs: AddWordCommandInputs,
):
    payload = NonCORWordGenerationInput(
        surface_form=inputs.normalized_surface,
        lemma_candidate=inputs.stored_lemma,
        pos_tag=inputs.selected_pos_tag,
        morphology=inputs.selected_morphology,
        sentence_context=None,
    )
    return runtime.translation.generate_non_cor_word_entries_batch([payload])[0]
