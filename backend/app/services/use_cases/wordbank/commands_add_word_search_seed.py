from __future__ import annotations

from dataclasses import dataclass

from app.api.schemas.v1.wordbank import AddWordResponse, MeaningContext, QueuedBackgroundTask, VerificationResult
from app.db.repositories import WordbankBackgroundJobRepository
from app.db.repositories.wordbank_models import LexemeMeaningRecord
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.meaning_sections import (
    MeaningAssignment,
    ensure_wordbank_meaning_compatibility,
    is_verb_like_pos_tag,
)
from app.services.use_cases.wordbank.queries_details import get_lemma_details
from app.services.use_cases.wordbank.runtime import WordbankRuntime
from app.services.use_cases.wordbank.verification_targets import (
    discover_word_page_verification_targets,
    queue_verification_targets,
)


@dataclass(frozen=True, slots=True)
class SearchSeedInputs:
    lemma: str
    surface: str
    cor_id: str | None
    cor_lemma_idx: int | None
    meaning_key: str | None
    gloss: str | None
    english_translation: str | None
    pos_tag: str | None
    morphology: str | None
    target_meaning_id: int | None


@dataclass(frozen=True, slots=True)
class SearchSeedMetadata:
    lemma_pos_tag: str | None
    lemma_morphology: str | None
    surface_pos_tag: str | None
    surface_morphology: str | None


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
    seed = _normalize_search_seed(search_seed)
    metadata = _resolve_search_seed_metadata(runtime, seed=seed)
    normalized_surface = normalize_token(surface_token)
    normalized_lemma = normalize_token(lemma_candidate or "") or normalized_surface
    if normalized_surface != seed.surface:
        raise ValueError("search_seed.surface must match surface_token")
    if normalized_lemma != seed.lemma:
        raise ValueError("search_seed.lemma must match lemma_candidate")

    lexeme_id, inserted_lexeme = runtime.repository.insert_or_load_lexeme(
        stored_lemma=seed.lemma,
        translation=seed.english_translation,
        provider="search_seed" if seed.english_translation else None,
        pos_tag=metadata.lemma_pos_tag,
        morphology=metadata.lemma_morphology,
        source="search",
    )
    _repair_lexeme_metadata_if_surface_derived(
        runtime,
        lexeme_id=lexeme_id,
        seed=seed,
        metadata=metadata,
    )
    meaning, meaning_record, inserted_meaning = _resolve_meaning_assignment(
        runtime,
        lexeme_id=lexeme_id,
        seed=seed,
        metadata=metadata,
    )
    if meaning_record is not None:
        _repair_meaning_metadata_if_surface_derived(
            runtime,
            meaning=meaning_record,
            seed=seed,
            metadata=metadata,
        )
    surface_form, inserted_surface_form = runtime.repository.insert_or_update_surface_form(
        lexeme_id=lexeme_id,
        meaning_id=meaning.id if meaning is not None else None,
        form=seed.surface,
        pos_tag=metadata.surface_pos_tag,
        morphology=metadata.surface_morphology,
        source="search",
    )
    inserted_cor_variant = False
    if seed.cor_id:
        inserted_cor_variant = runtime.repository.insert_surface_form_cor_variant(
            surface_form_id=surface_form.id,
            cor_id=seed.cor_id,
        )

    if inserted_lexeme or inserted_surface_form or inserted_cor_variant or meaning is not None:
        runtime.nlp.add_user_lexeme(seed.lemma)
    runtime.nlp.invalidate_pos_cache(seed.lemma, seed.surface)
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
    inserted_any = inserted_lexeme or inserted_surface_form or inserted_cor_variant or inserted_meaning
    return AddWordResponse(
        status="inserted" if inserted_any else "exists",
        stored_lemma=seed.lemma,
        stored_surface_form=seed.surface,
        source="manual",
        message=(
            f"Added '{seed.lemma}' to wordbank."
            if inserted_any
            else f"'{seed.lemma}' is already in the wordbank."
        ),
        meaning=(
            MeaningContext(
                id=meaning.id,
                meaning_key=meaning.meaning_key,
                gloss=meaning.gloss,
                english_translation=meaning.english_translation,
            )
            if meaning is not None
            else None
        ),
        verification=verification,
        queued_verification_targets=queued_verification_targets,
        pronunciation=pronunciation,
        saved_snapshot=saved_snapshot,
    )


def _normalize_search_seed(search_seed: dict[str, object]) -> SearchSeedInputs:
    lemma = normalize_token(_required_string(search_seed, "lemma"))
    surface = normalize_token(_required_string(search_seed, "surface"))
    if not lemma or not surface:
        raise ValueError("search_seed.lemma and search_seed.surface are required")
    target_meaning_id = _optional_int(search_seed, "target_meaning_id")
    return SearchSeedInputs(
        lemma=lemma,
        surface=surface,
        cor_id=_optional_spaced_string(search_seed, "cor_id"),
        cor_lemma_idx=_optional_int(search_seed, "cor_lemma_idx"),
        meaning_key=_optional_normalized_string(search_seed, "meaning_key"),
        gloss=_optional_normalized_string(search_seed, "gloss"),
        english_translation=_optional_normalized_string(search_seed, "english_translation"),
        pos_tag=_optional_upper_string(search_seed, "pos_tag"),
        morphology=_optional_spaced_string(search_seed, "morphology"),
        target_meaning_id=target_meaning_id,
    )


def _resolve_meaning_assignment(
    runtime: WordbankRuntime,
    *,
    lexeme_id: int,
    seed: SearchSeedInputs,
    metadata: SearchSeedMetadata,
) -> tuple[MeaningAssignment | None, LexemeMeaningRecord | None, bool]:
    if seed.target_meaning_id is not None:
        for meaning in runtime.repository.list_lexeme_meanings(lexeme_id):
            if meaning.id == seed.target_meaning_id:
                return MeaningAssignment(
                    id=meaning.id,
                    meaning_key=meaning.meaning_key,
                    gloss=meaning.gloss,
                    english_translation=meaning.english_translation,
                ), meaning, False
        raise ValueError(f"Meaning '{seed.target_meaning_id}' was not found for lemma '{seed.lemma}'")

    if is_verb_like_pos_tag(seed.pos_tag):
        return None, None, False

    meaning_key = seed.meaning_key or seed.gloss or seed.lemma
    record, inserted = runtime.repository.upsert_lexeme_meaning(
        lexeme_id=lexeme_id,
        meaning_key=meaning_key,
        cor_lemma_idx=seed.cor_lemma_idx,
        gloss=seed.gloss,
        english_translation=seed.english_translation,
        pos_tag=metadata.lemma_pos_tag,
        morphology=metadata.lemma_morphology,
    )
    return MeaningAssignment(
        id=record.id,
        meaning_key=record.meaning_key,
        gloss=record.gloss,
        english_translation=record.english_translation,
    ), record, inserted


def _resolve_search_seed_metadata(
    runtime: WordbankRuntime,
    *,
    seed: SearchSeedInputs,
) -> SearchSeedMetadata:
    lemma_entry = None
    if seed.cor_lemma_idx is not None:
        lemma_entry = runtime.cor.best_cor_local_lemma_entry(
            lemma_idx=seed.cor_lemma_idx,
            lemma=seed.lemma,
            preferred_pos_tag=seed.pos_tag,
        )
    return SearchSeedMetadata(
        lemma_pos_tag=lemma_entry.pos_tag if lemma_entry is not None else seed.pos_tag,
        lemma_morphology=lemma_entry.morphology if lemma_entry is not None else seed.morphology,
        surface_pos_tag=seed.pos_tag,
        surface_morphology=seed.morphology,
    )


def _repair_lexeme_metadata_if_surface_derived(
    runtime: WordbankRuntime,
    *,
    lexeme_id: int,
    seed: SearchSeedInputs,
    metadata: SearchSeedMetadata,
) -> None:
    lexeme = runtime.repository.get_lexeme(seed.lemma)
    if lexeme is None or lexeme.source != "search":
        return
    if not _should_replace_surface_derived_metadata(
        current_pos_tag=lexeme.pos_tag,
        current_morphology=lexeme.morphology,
        surface_pos_tag=metadata.surface_pos_tag,
        surface_morphology=metadata.surface_morphology,
        canonical_pos_tag=metadata.lemma_pos_tag,
        canonical_morphology=metadata.lemma_morphology,
    ):
        return
    runtime.repository.replace_lexeme_metadata(
        lexeme_id=lexeme_id,
        pos_tag=metadata.lemma_pos_tag,
        morphology=metadata.lemma_morphology,
    )


def _repair_meaning_metadata_if_surface_derived(
    runtime: WordbankRuntime,
    *,
    meaning: LexemeMeaningRecord,
    seed: SearchSeedInputs,
    metadata: SearchSeedMetadata,
) -> None:
    if seed.target_meaning_id is None and meaning.cor_lemma_idx != seed.cor_lemma_idx:
        return
    if not _should_replace_surface_derived_metadata(
        current_pos_tag=meaning.pos_tag,
        current_morphology=meaning.morphology,
        surface_pos_tag=metadata.surface_pos_tag,
        surface_morphology=metadata.surface_morphology,
        canonical_pos_tag=metadata.lemma_pos_tag,
        canonical_morphology=metadata.lemma_morphology,
    ):
        return
    runtime.repository.replace_lexeme_meaning_metadata(
        meaning_id=meaning.id,
        pos_tag=metadata.lemma_pos_tag,
        morphology=metadata.lemma_morphology,
    )


def _should_replace_surface_derived_metadata(
    *,
    current_pos_tag: str | None,
    current_morphology: str | None,
    surface_pos_tag: str | None,
    surface_morphology: str | None,
    canonical_pos_tag: str | None,
    canonical_morphology: str | None,
) -> bool:
    current = (current_pos_tag, current_morphology)
    surface = (surface_pos_tag, surface_morphology)
    canonical = (canonical_pos_tag, canonical_morphology)
    return canonical != surface and current == surface


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


def _required_string(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"search_seed.{key} is required")
    return value


def _optional_normalized_string(payload: dict[str, object], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"search_seed.{key} is invalid")
    cleaned = normalize_token(value)
    return cleaned or None


def _optional_spaced_string(payload: dict[str, object], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"search_seed.{key} is invalid")
    cleaned = _normalize_space(value)
    return cleaned or None


def _optional_upper_string(payload: dict[str, object], key: str) -> str | None:
    value = _optional_spaced_string(payload, key)
    return value.upper() if value else None


def _optional_int(payload: dict[str, object], key: str) -> int | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, int):
        raise ValueError(f"search_seed.{key} is invalid")
    return value
