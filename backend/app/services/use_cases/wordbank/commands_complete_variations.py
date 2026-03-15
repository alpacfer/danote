from __future__ import annotations

from app.api.schemas.v1.wordbank import CompleteVariationsResponse
from app.db.repositories import WordbankBackgroundJobRepository
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.noun_variations import (
    TARGET_NOUN_SLOTS,
    noun_meaning_context_from_rows,
    resolve_target_noun_slot_entries,
)
from app.services.use_cases.wordbank.runtime import WordbankRuntime
from app.services.use_cases.wordbank.search_seed_persistence import (
    SearchSeedInputs,
    persist_search_seed_surface_form,
)
from app.services.use_cases.wordbank.verification_targets import (
    VerificationTarget,
    queue_verification_targets,
)


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
    slot_entries = resolve_target_noun_slot_entries(runtime.cor, context=context)
    if not slot_entries:
        return CompleteVariationsResponse(
            status="skipped",
            stored_lemma=normalized_lemma,
            meaning_id=meaning_id,
            added_surface_forms=[],
            queued_pronunciation_forms=[],
            message=f"No COR noun paradigm entries were found for meaning #{meaning_id}.",
        )

    existing_forms = {
        normalize_token(row.form)
        for row in runtime.repository.list_surface_forms(context.lexeme_id)
        if row.meaning_id == meaning_id and normalize_token(row.form)
    }
    added_surface_forms: list[str] = []
    queued_pronunciation_forms: list[str] = []
    pronunciation_repository = WordbankBackgroundJobRepository(runtime.db_path)

    for slot_name, _number, _definite in TARGET_NOUN_SLOTS:
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

    _delete_meaning_surface_verification_records(runtime, context=context)
    queue_verification_targets(
        runtime,
        stored_lemma=context.lemma,
        targets=(VerificationTarget(meaning_id=context.meaning_id, stored_surface_form=None),),
        review_intent="complete_variations",
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
):
    lexeme = runtime.repository.get_lexeme(stored_lemma)
    if lexeme is None:
        raise LookupError(f"Lemma '{stored_lemma}' was not found")
    meaning = next(
        (item for item in runtime.repository.list_lexeme_meanings(lexeme.id) if item.id == meaning_id),
        None,
    )
    if meaning is None:
        raise LookupError(f"Meaning '{meaning_id}' was not found for lemma '{stored_lemma}'")
    if (meaning.pos_tag or lexeme.pos_tag or "").upper() != "NOUN":
        raise ValueError("unsupported")
    if meaning.cor_lemma_idx is None:
        raise RuntimeError("missing_cor_identity")
    return noun_meaning_context_from_rows(
        source_lexeme={
            "id": lexeme.id,
            "lemma": lexeme.lemma,
            "english_translation": lexeme.english_translation,
            "pos_tag": lexeme.pos_tag,
        },
        source_meaning={
            "id": meaning.id,
            "cor_lemma_idx": meaning.cor_lemma_idx,
            "gloss": meaning.gloss,
            "english_translation": meaning.english_translation,
            "pos_tag": meaning.pos_tag,
        },
    )
def _updated_message(stored_lemma: str, added_surface_forms: list[str]) -> str:
    if len(added_surface_forms) == 1:
        return f"Completed noun variations for '{stored_lemma}' with {added_surface_forms[0]}."
    return f"Completed noun variations for '{stored_lemma}'."


def _delete_meaning_surface_verification_records(
    runtime: WordbankRuntime,
    *,
    context,
) -> None:
    for row in runtime.repository.list_surface_forms(context.lexeme_id):
        if row.meaning_id != context.meaning_id:
            continue
        normalized_form = normalize_token(row.form)
        if not normalized_form:
            continue
        runtime.repository.delete_verification_record(
            lexeme_id=context.lexeme_id,
            meaning_id=context.meaning_id,
            stored_surface_form=normalized_form,
        )
