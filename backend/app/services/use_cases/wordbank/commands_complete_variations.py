from __future__ import annotations

from dataclasses import dataclass

from app.api.schemas.v1.wordbank import CompleteVariationsResponse
from app.db.repositories import WordbankBackgroundJobRepository
from app.services.cor_local import CORLocalEntry
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.runtime import WordbankRuntime
from app.services.use_cases.wordbank.search_seed_persistence import (
    SearchSeedInputs,
    persist_search_seed_surface_form,
)
from app.services.use_cases.wordbank.verification_targets import (
    discover_word_page_verification_targets,
    queue_verification_targets,
)

_TARGET_NOUN_SLOTS = (
    ("singular_definite", "Sing", "Def"),
    ("plural_indefinite", "Plur", "Ind"),
    ("plural_definite", "Plur", "Def"),
)


@dataclass(frozen=True, slots=True)
class _MeaningContext:
    lexeme_id: int
    lemma: str
    meaning_id: int
    gloss: str | None
    english_translation: str | None
    cor_lemma_idx: int


def complete_meaning_variations(
    runtime: WordbankRuntime,
    *,
    stored_lemma: str,
    meaning_id: int,
) -> CompleteVariationsResponse:
    normalized_lemma = normalize_token(stored_lemma)
    if not normalized_lemma:
        raise ValueError("stored_lemma is required")
    if meaning_id < 1:
        raise ValueError("meaning_id must be >= 1")

    context = _load_meaning_context(runtime, stored_lemma=normalized_lemma, meaning_id=meaning_id)
    entries = _candidate_entries_for_meaning(runtime, context=context)
    if not entries:
        return CompleteVariationsResponse(
            status="skipped",
            stored_lemma=normalized_lemma,
            meaning_id=meaning_id,
            added_surface_forms=[],
            queued_pronunciation_forms=[],
            message=f"No COR noun paradigm entries were found for meaning #{meaning_id}.",
        )

    slot_entries = _entries_by_target_slot(entries)
    if not slot_entries:
        return CompleteVariationsResponse(
            status="skipped",
            stored_lemma=normalized_lemma,
            meaning_id=meaning_id,
            added_surface_forms=[],
            queued_pronunciation_forms=[],
            message=f"No supported noun variations were found for meaning #{meaning_id}.",
        )

    existing_forms = {
        normalize_token(row.form)
        for row in runtime.repository.list_surface_forms(context.lexeme_id)
        if row.meaning_id == meaning_id and normalize_token(row.form)
    }
    added_surface_forms: list[str] = []
    queued_pronunciation_forms: list[str] = []
    pronunciation_repository = WordbankBackgroundJobRepository(runtime.db_path)

    for slot_name, _number, _definite in _TARGET_NOUN_SLOTS:
        entry = slot_entries.get(slot_name)
        if entry is None:
            continue
        normalized_form = normalize_token(entry.form)
        if not normalized_form or normalized_form in existing_forms:
            continue
        persist_result = persist_search_seed_surface_form(
            runtime,
            seed=SearchSeedInputs(
                lemma=context.lemma,
                surface=entry.form,
                cor_id=entry.cor_id,
                cor_lemma_idx=context.cor_lemma_idx,
                meaning_key=None,
                gloss=context.gloss or normalize_token(entry.gloss or ""),
                english_translation=context.english_translation,
                pos_tag=entry.pos_tag,
                morphology=entry.morphology,
                target_meaning_id=meaning_id,
            ),
        )
        if not persist_result.inserted_any:
            existing_forms.add(normalized_form)
            continue
        existing_forms.add(normalized_form)
        added_surface_forms.append(entry.form)
        pronunciation = runtime.pronunciation.queued_pronunciation_result(context.lemma, entry.form)
        if pronunciation.status == "queued":
            pronunciation_repository.enqueue(
                job_type="generate_pronunciation",
                dedupe_key=f"generate_pronunciation::{context.lemma}::{normalized_form}",
                payload={
                    "stored_lemma": context.lemma,
                    "stored_surface_form": normalized_form,
                },
            )
            queued_pronunciation_forms.append(entry.form)

    if not added_surface_forms:
        return CompleteVariationsResponse(
            status="skipped",
            stored_lemma=normalized_lemma,
            meaning_id=meaning_id,
            added_surface_forms=[],
            queued_pronunciation_forms=[],
            message=f"No missing noun variations were found for '{normalized_lemma}'.",
        )

    queue_verification_targets(
        runtime,
        stored_lemma=context.lemma,
        targets=discover_word_page_verification_targets(
            runtime,
            stored_lemma=context.lemma,
        ),
    )
    return CompleteVariationsResponse(
        status="updated",
        stored_lemma=normalized_lemma,
        meaning_id=meaning_id,
        added_surface_forms=added_surface_forms,
        queued_pronunciation_forms=queued_pronunciation_forms,
        message=_updated_message(normalized_lemma, added_surface_forms),
    )


def _load_meaning_context(
    runtime: WordbankRuntime,
    *,
    stored_lemma: str,
    meaning_id: int,
) -> _MeaningContext:
    lexeme = runtime.repository.get_lexeme(stored_lemma)
    if lexeme is None:
        raise LookupError(f"Lemma '{stored_lemma}' was not found")
    meaning = next(
        (item for item in runtime.repository.list_lexeme_meanings(lexeme.id) if item.id == meaning_id),
        None,
    )
    if meaning is None:
        raise LookupError(f"Meaning '{meaning_id}' was not found for lemma '{stored_lemma}'")
    pos_tag = (meaning.pos_tag or lexeme.pos_tag or "").upper()
    if pos_tag != "NOUN":
        raise ValueError("unsupported")
    if meaning.cor_lemma_idx is None:
        raise RuntimeError("missing_cor_identity")
    return _MeaningContext(
        lexeme_id=lexeme.id,
        lemma=lexeme.lemma,
        meaning_id=meaning.id,
        gloss=meaning.gloss,
        english_translation=meaning.english_translation or lexeme.english_translation,
        cor_lemma_idx=meaning.cor_lemma_idx,
    )


def _candidate_entries_for_meaning(
    runtime: WordbankRuntime,
    *,
    context: _MeaningContext,
) -> list[CORLocalEntry]:
    entries = runtime.cor.cor_local_entries_for_lemma_idx(
        lemma_idx=context.cor_lemma_idx,
        lemma=context.lemma,
        preferred_pos_tag="NOUN",
    )
    if not entries:
        return []
    matching_lemma = [
        entry for entry in entries if normalize_token(entry.lemma) == context.lemma and entry.pos_tag == "NOUN"
    ]
    if not matching_lemma:
        return []
    normalized_gloss = normalize_token(context.gloss or "")
    if not normalized_gloss:
        return matching_lemma
    gloss_matches = [
        entry for entry in matching_lemma if normalize_token(entry.gloss or "") == normalized_gloss
    ]
    return gloss_matches or matching_lemma


def _entries_by_target_slot(entries: list[CORLocalEntry]) -> dict[str, CORLocalEntry]:
    by_slot: dict[str, CORLocalEntry] = {}
    for entry in entries:
        slot = _noun_slot(entry)
        if slot is None or slot in by_slot:
            continue
        by_slot[slot] = entry
    return by_slot


def _noun_slot(entry: CORLocalEntry) -> str | None:
    features = entry.features or _morphology_features(entry.morphology)
    number = features.get("Number")
    definite = features.get("Definite")
    if number == "Sing" and definite == "Ind":
        return "singular_indefinite"
    if number == "Sing" and definite == "Def":
        return "singular_definite"
    if number == "Plur" and definite == "Ind":
        return "plural_indefinite"
    if number == "Plur" and definite == "Def":
        return "plural_definite"
    return None


def _morphology_features(morphology: str | None) -> dict[str, str]:
    if not morphology:
        return {}
    features: dict[str, str] = {}
    for item in morphology.split("|"):
        key, _, value = item.partition("=")
        if key and value and key not in features:
            features[key] = value
    return features


def _updated_message(stored_lemma: str, added_surface_forms: list[str]) -> str:
    if len(added_surface_forms) == 1:
        return f"Completed noun variations for '{stored_lemma}' with {added_surface_forms[0]}."
    return f"Completed noun variations for '{stored_lemma}'."
