from __future__ import annotations

from app.api.schemas.v1.wordbank import AddWordResponse, MeaningContext, VerificationResult
from app.services.gemini_translation import NonCORWordGenerationInput
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.meaning_sections import ensure_wordbank_meaning_compatibility
from app.services.use_cases.wordbank.pronunciation_queue import queue_pronunciation_generation
from app.services.use_cases.wordbank.queries_details import get_lemma_details
from app.services.use_cases.wordbank.related_words_queue import queue_related_words_resolution
from app.services.use_cases.wordbank.runtime import WordbankRuntime
from app.services.use_cases.wordbank.search_seed_persistence import (
    SearchSeedInputs,
    normalize_search_seed,
    persist_search_seed_surface_form,
)
from app.services.use_cases.wordbank.verification_targets import (
    discover_word_page_verification_targets,
    queue_verification_targets,
)

def add_word_from_search_seed(
    runtime: WordbankRuntime,
    *,
    surface_token: str,
    lemma_candidate: str | None,
    search_seed: dict[str, object],
    queue_verification: bool = True,
) -> AddWordResponse:
    ensure_wordbank_meaning_compatibility(runtime)
    seed = normalize_search_seed(search_seed)
    normalized_surface = normalize_token(surface_token)
    normalized_lemma = normalize_token(lemma_candidate or "") or normalized_surface
    if normalized_surface != seed.surface:
        raise ValueError("search_seed.surface must match surface_token")
    if normalized_lemma != seed.lemma:
        raise ValueError("search_seed.lemma must match lemma_candidate")

    if seed.dictionary_status == "generated_non_cor" and seed.morphology is None:
        seed = _enrich_non_cor_seed_morphology(runtime, seed)

    persist_result = persist_search_seed_surface_form(runtime, seed=seed)
    verification = (
        runtime.verification.queued_verification_result(
            stored_surface_form=seed.surface,
        )
        if queue_verification
        else None
    )
    queued_verification_targets = (
        queue_verification_targets(
            runtime,
            stored_lemma=seed.lemma,
            targets=discover_word_page_verification_targets(
                runtime,
                stored_lemma=seed.lemma,
            ),
        )
        if queue_verification
        else []
    )
    pronunciation = runtime.pronunciation.queued_pronunciation_result(seed.lemma, seed.surface)
    queued_pronunciation_forms = queue_pronunciation_generation(
        runtime,
        stored_lemma=seed.lemma,
        requested_forms=(seed.surface,),
    )
    queue_related_words_resolution(
        runtime,
        stored_lemma=seed.lemma,
    )
    saved_snapshot = get_lemma_details(runtime, seed.lemma)
    return AddWordResponse(
        status="inserted" if persist_result.inserted_any else "exists",
        stored_lemma=seed.lemma,
        stored_surface_form=seed.surface,
        source="manual",
        message=(
            f"Added '{seed.lemma}' to wordbank."
            if persist_result.inserted_any
            else f"'{seed.lemma}' is already in the wordbank."
        ),
        meaning=(
            MeaningContext(
                id=persist_result.meaning.id,
                meaning_key=persist_result.meaning.meaning_key,
                gloss=persist_result.meaning.gloss,
                english_translation=persist_result.meaning.english_translation,
            )
            if persist_result.meaning is not None
            else None
        ),
        verification=verification,
        queued_verification_targets=queued_verification_targets,
        queued_pronunciation_forms=queued_pronunciation_forms,
        pronunciation=pronunciation,
        saved_snapshot=saved_snapshot,
    )


def _enrich_non_cor_seed_morphology(runtime: WordbankRuntime, seed: SearchSeedInputs) -> SearchSeedInputs:
    payload = NonCORWordGenerationInput(
        surface_form=seed.surface,
        lemma_candidate=seed.lemma,
        pos_tag=seed.pos_tag,
        morphology=None,
        sentence_context=None,
    )
    results = runtime.translation.generate_non_cor_word_entries_batch([payload])
    generated = results[0] if results else None
    if generated is None:
        return seed
    return SearchSeedInputs(
        lemma=seed.lemma,
        surface=seed.surface,
        cor_id=seed.cor_id,
        cor_lemma_idx=seed.cor_lemma_idx,
        dictionary_status=seed.dictionary_status,
        meaning_key=seed.meaning_key,
        gloss=seed.gloss,
        english_translation=seed.english_translation or generated.english_translation,
        pos_tag=generated.surface_pos_tag or generated.pos_tag or seed.pos_tag,
        morphology=generated.surface_morphology or generated.morphology,
        target_meaning_id=seed.target_meaning_id,
    )
