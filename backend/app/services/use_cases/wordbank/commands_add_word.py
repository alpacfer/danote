from __future__ import annotations

from app.api.schemas.v1.wordbank import AddWordResponse
from app.services.cor_local import CORLocalEntry
from app.services.gemini_translation import NonCORWordGenerationInput
from app.services.use_cases.static_builtin_words import (
    StaticBuiltinSense,
    ensure_static_builtin_sense,
    select_static_builtin_sense,
)
from app.services.use_cases.static_hv_words import StaticHvWord, static_hv_word_for_token
from app.services.use_cases.static_pronouns import StaticPronoun, static_pronoun_for_token
from app.services.use_cases.wordbank.add_word_canonicalisation import (
    canonicalise_lemma_candidate,
)
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
    resolve_meaning,
    resolve_meaning_translation,
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
    is_formal_i = surface_token.strip() == "I" or (lemma_candidate or "").strip() == "I"
    if not is_formal_i:
        static_builtin = select_static_builtin_sense(surface_token, pos_tag=pos_tag, morphology=morphology)
        if static_builtin is not None:
            return _add_static_builtin(runtime, surface_token=surface_token, sense=static_builtin)

    static_hv_word = static_hv_word_for_token(surface_token) or static_hv_word_for_token(lemma_candidate)
    if static_hv_word is not None:
        return _add_static_hv_word(runtime, surface_token=surface_token, hv_word=static_hv_word)

    static_pronoun = static_pronoun_for_token(surface_token) or static_pronoun_for_token(lemma_candidate)
    if static_pronoun is not None:
        return _add_static_pronoun(runtime, surface_token=surface_token, pronoun=static_pronoun)

    static_builtin = select_static_builtin_sense(surface_token, pos_tag=pos_tag, morphology=morphology)
    if static_builtin is not None:
        return _add_static_builtin(runtime, surface_token=surface_token, sense=static_builtin)

    if search_seed is not None:
        return add_word_from_search_seed(
            runtime,
            surface_token=surface_token,
            lemma_candidate=lemma_candidate,
            search_seed=search_seed,
            queue_verification=queue_verification,
        )
    ensure_wordbank_meaning_compatibility(runtime)
    lemma_candidate = canonicalise_lemma_candidate(
        runtime,
        surface_token=surface_token,
        lemma_candidate=lemma_candidate,
        cor_id=cor_id,
        pos_tag=pos_tag,
    )
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

    meaning_resolution = resolve_meaning(
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


def _add_static_hv_word(
    runtime: WordbankRuntime,
    *,
    surface_token: str,
    hv_word: StaticHvWord,
) -> AddWordResponse:
    actual_surface = static_hv_word_for_token(surface_token)
    normalized_surface = actual_surface.lemma if actual_surface is not None else hv_word.lemma
    lexeme_id, inserted_lexeme = runtime.repository.insert_or_load_lexeme(
        stored_lemma=hv_word.lemma,
        translation=hv_word.english_translation,
        provider="static_hv_word",
        pos_tag=hv_word.pos_tag,
        morphology=hv_word.morphology,
        dictionary_status="unknown",
    )
    _surface_form, inserted_surface_form = runtime.repository.insert_or_update_surface_form(
        lexeme_id=lexeme_id,
        meaning_id=None,
        form=normalized_surface,
        pos_tag=actual_surface.pos_tag if actual_surface is not None else hv_word.pos_tag,
        morphology=actual_surface.morphology if actual_surface is not None else hv_word.morphology,
        source="static",
    )
    runtime.nlp.add_user_lexeme(hv_word.lemma)
    runtime.nlp.invalidate_pos_cache(hv_word.lemma, normalized_surface)
    return build_add_word_response(
        runtime=runtime,
        inputs=AddWordCommandInputs(
            normalized_surface=normalized_surface,
            stored_lemma=hv_word.lemma,
            normalized_cor_id=None,
            selected_pos_tag=hv_word.pos_tag,
            selected_morphology=hv_word.morphology,
        ),
        write_result=AddWordWriteResult(
            inserted_lexeme=inserted_lexeme,
            inserted_meaning=False,
            inserted_surface_form=inserted_surface_form,
            inserted_lemma_surface_form=False,
            inserted_cor_variant=False,
        ),
        meaning=None,
        verification=None,
        queued_verification_targets=[],
        queued_pronunciation_forms=[],
        pronunciation=None,
    )


def _add_static_pronoun(
    runtime: WordbankRuntime,
    *,
    surface_token: str,
    pronoun: StaticPronoun,
) -> AddWordResponse:
    actual_surface = static_pronoun_for_token(surface_token)
    normalized_surface = actual_surface.lemma if actual_surface is not None else pronoun.lemma
    lexeme_id, inserted_lexeme = runtime.repository.insert_or_load_lexeme(
        stored_lemma=pronoun.lemma,
        translation=pronoun.english_translation,
        provider="static_pronoun",
        pos_tag=pronoun.pos_tag,
        morphology=pronoun.morphology,
        dictionary_status="unknown",
    )
    _surface_form, inserted_surface_form = runtime.repository.insert_or_update_surface_form(
        lexeme_id=lexeme_id,
        meaning_id=None,
        form=normalized_surface,
        pos_tag=actual_surface.pos_tag if actual_surface is not None else pronoun.pos_tag,
        morphology=actual_surface.morphology if actual_surface is not None else pronoun.morphology,
        source="static",
    )
    runtime.nlp.add_user_lexeme(pronoun.lemma)
    runtime.nlp.invalidate_pos_cache(pronoun.lemma, normalized_surface)
    return build_add_word_response(
        runtime=runtime,
        inputs=AddWordCommandInputs(
            normalized_surface=normalized_surface,
            stored_lemma=pronoun.lemma,
            normalized_cor_id=None,
            selected_pos_tag=pronoun.pos_tag,
            selected_morphology=pronoun.morphology,
        ),
        write_result=AddWordWriteResult(
            inserted_lexeme=inserted_lexeme,
            inserted_meaning=False,
            inserted_surface_form=inserted_surface_form,
            inserted_lemma_surface_form=False,
            inserted_cor_variant=False,
        ),
        meaning=None,
        verification=None,
        queued_verification_targets=[],
        queued_pronunciation_forms=[],
        pronunciation=None,
    )


def _add_static_builtin(
    runtime: WordbankRuntime,
    *,
    surface_token: str,
    sense: StaticBuiltinSense,
) -> AddWordResponse:
    normalized_surface = sense.lemma
    inserted_lexeme = runtime.repository.get_lexeme(sense.lemma) is None
    lexeme_id, meaning_id = ensure_static_builtin_sense(runtime, sense)
    runtime.nlp.add_user_lexeme(sense.lemma)
    runtime.nlp.invalidate_pos_cache(sense.lemma, normalized_surface)
    meaning = runtime.repository.get_lexeme_meaning(meaning_id) if meaning_id is not None else None
    return build_add_word_response(
        runtime=runtime,
        inputs=AddWordCommandInputs(
            normalized_surface=normalized_surface,
            stored_lemma=sense.lemma,
            normalized_cor_id=None,
            selected_pos_tag=sense.pos_tag,
            selected_morphology=sense.morphology,
        ),
        write_result=AddWordWriteResult(
            inserted_lexeme=inserted_lexeme,
            inserted_meaning=inserted_lexeme and meaning_id is not None,
            inserted_surface_form=inserted_lexeme,
            inserted_lemma_surface_form=False,
            inserted_cor_variant=False,
        ),
        meaning=meaning,
        verification=None,
        queued_verification_targets=[],
        queued_pronunciation_forms=[],
        pronunciation=None,
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
