from __future__ import annotations

from app.api.schemas.v1.wordbank import AddWordResponse, MeaningContext, QueuedBackgroundTask, VerificationResult
from app.core.errors import ConflictError
from app.db.repositories import WordbankBackgroundJobRepository
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.meaning_sections import ensure_wordbank_meaning_compatibility
from app.services.use_cases.wordbank.queries_details import get_lemma_details
from app.services.use_cases.wordbank.runtime import WordbankRuntime
from app.services.use_cases.wordbank.search_seed_persistence import (
    normalize_search_seed,
    persist_search_seed_surface_form,
)
from app.services.use_cases.wordbank.verification_targets import (
    discover_word_page_verification_targets,
    queue_verification_targets,
)


def _normalize_space(value: str | None) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.strip().split())


def add_word_from_search_seed(
    runtime: WordbankRuntime,
    *,
    surface_token: str,
    lemma_candidate: str | None,
    search_seed: dict[str, object],
) -> AddWordResponse:
    ensure_wordbank_meaning_compatibility(runtime)
    seed = normalize_search_seed(search_seed)
    normalized_surface = normalize_token(surface_token)
    normalized_lemma = normalize_token(lemma_candidate or "") or normalized_surface
    if normalized_surface != seed.surface:
        raise ValueError("search_seed.surface must match surface_token")
    if normalized_lemma != seed.lemma:
        raise ValueError("search_seed.lemma must match lemma_candidate")
    if not _normalize_space(seed.english_translation):
        raise ConflictError("Search save is unavailable until translation finishes generating.")

    persist_result = persist_search_seed_surface_form(runtime, seed=seed)
    verification = runtime.verification.queued_verification_result(
        stored_surface_form=seed.surface,
    )
    queued_verification_targets = queue_verification_targets(
        runtime,
        stored_lemma=seed.lemma,
        targets=discover_word_page_verification_targets(
            runtime,
            stored_lemma=seed.lemma,
        ),
    )
    pronunciation = runtime.pronunciation.queued_pronunciation_result(seed.lemma, seed.surface)
    _enqueue_background_jobs(
        runtime,
        stored_lemma=seed.lemma,
        stored_surface_form=seed.surface,
        pronunciation=pronunciation,
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
        pronunciation=pronunciation,
        saved_snapshot=saved_snapshot,
    )


def _enqueue_background_jobs(
    runtime: WordbankRuntime,
    *,
    stored_lemma: str,
    stored_surface_form: str | None,
    pronunciation: QueuedBackgroundTask | None,
) -> None:
    repository = WordbankBackgroundJobRepository(runtime.db_path)
    normalized_surface = normalize_token(stored_surface_form or "") or None
    if pronunciation is not None and pronunciation.status == "queued":
        repository.enqueue(
            job_type="generate_pronunciation",
            dedupe_key=f"generate_pronunciation::{stored_lemma}::{normalized_surface or ''}",
            payload={
                "stored_lemma": stored_lemma,
                "stored_surface_form": normalized_surface,
            },
        )
