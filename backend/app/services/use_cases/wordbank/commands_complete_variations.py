from __future__ import annotations

from app.api.schemas.v1.wordbank import CompleteVariationsResponse
from app.services.gemini_translation import (
    NonCORVariationCandidate,
    NonCORVariationGenerationInput,
)
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.paradigm_variations import (
    meaning_context_from_rows,
)
from app.services.use_cases.wordbank.pronunciation_queue import queue_pronunciation_generation
from app.services.use_cases.wordbank.runtime import WordbankRuntime
from app.services.use_cases.wordbank.search_seed_persistence import (
    SearchSeedInputs,
    persist_search_seed_surface_form,
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

    lexeme, meaning = _load_lexeme_and_meaning(runtime, stored_lemma=normalized_lemma, meaning_id=meaning_id)
    if (meaning.pos_tag or lexeme.pos_tag or "").upper() not in {"NOUN", "ADJ", "VERB"}:
        return CompleteVariationsResponse(
            status="skipped",
            stored_lemma=normalized_lemma,
            meaning_id=meaning_id,
            added_surface_forms=[],
            queued_pronunciation_forms=[],
            queued_verification_targets=[],
            message="Complete variations is only available for noun, adjective, and verb meanings.",
        )
    if runtime.translation._gemini_word_translation_service is None:
        return CompleteVariationsResponse(
            status="skipped",
            stored_lemma=normalized_lemma,
            meaning_id=meaning_id,
            added_surface_forms=[],
            queued_pronunciation_forms=[],
            queued_verification_targets=[],
            message="Complete variations requires Gemini.",
        )
    return _complete_gemini_variations(runtime, lexeme=lexeme, meaning=meaning)


def _load_lexeme_and_meaning(
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
    return lexeme, meaning


def _complete_gemini_variations(
    runtime: WordbankRuntime,
    *,
    lexeme,
    meaning,
) -> CompleteVariationsResponse:
    context = meaning_context_from_rows(
        source_lexeme={
            "id": lexeme.id,
            "lemma": lexeme.lemma,
            "english_translation": lexeme.english_translation,
            "pos_tag": meaning.pos_tag or lexeme.pos_tag,
        },
        source_meaning={
            "id": meaning.id,
            "cor_lemma_idx": 1,
            "gloss": meaning.gloss,
            "english_translation": meaning.english_translation,
            "pos_tag": meaning.pos_tag or lexeme.pos_tag,
        },
        allow_missing_cor_identity=True,
    )
    completion_gate_message = _complete_variations_gate_message(runtime, context=context)
    if completion_gate_message is not None:
        return CompleteVariationsResponse(
            status="skipped",
            stored_lemma=lexeme.lemma,
            meaning_id=meaning.id,
            added_surface_forms=[],
            queued_pronunciation_forms=[],
            queued_verification_targets=[],
            message=completion_gate_message,
        )

    existing_rows = {
        normalize_token(row.form): row
        for row in runtime.repository.list_surface_forms(lexeme.id)
        if row.meaning_id == meaning.id and normalize_token(row.form)
    }
    generated = runtime.translation.complete_non_cor_meaning_variations(
        NonCORVariationGenerationInput(
            stored_lemma=lexeme.lemma,
            english_translation=meaning.english_translation or lexeme.english_translation,
            meaning_key=meaning.meaning_key,
            gloss=meaning.gloss or meaning.meaning_key,
            pos_tag=meaning.pos_tag or lexeme.pos_tag,
            morphology=meaning.morphology or lexeme.morphology,
            existing_forms=[
                NonCORVariationCandidate(
                    form=row.form,
                    pos_tag=row.pos_tag,
                    morphology=row.morphology,
                )
                for row in existing_rows.values()
            ],
        )
    )

    added_surface_forms: list[str] = []
    for candidate in generated.forms:
        normalized_form = normalize_token(candidate.form)
        if not normalized_form or normalized_form in existing_rows:
            continue
        persist_result = persist_search_seed_surface_form(
            runtime,
            seed=SearchSeedInputs(
                lemma=lexeme.lemma,
                surface=normalized_form,
                cor_id=None,
                cor_lemma_idx=None,
                dictionary_status=meaning.dictionary_status,
                meaning_key=meaning.meaning_key,
                gloss=meaning.gloss,
                english_translation=meaning.english_translation or lexeme.english_translation,
                pos_tag=candidate.pos_tag or meaning.pos_tag or lexeme.pos_tag,
                morphology=candidate.morphology or meaning.morphology or lexeme.morphology,
                target_meaning_id=meaning.id,
            ),
        )
        if not persist_result.inserted_any:
            continue
        existing_rows[normalized_form] = persist_result.surface_form
        added_surface_forms.append(normalized_form)

    if not added_surface_forms:
        return CompleteVariationsResponse(
            status="skipped",
            stored_lemma=lexeme.lemma,
            meaning_id=meaning.id,
            added_surface_forms=[],
            queued_pronunciation_forms=[],
            queued_verification_targets=[],
            message=f"No missing {context.paradigm_kind} variations were found for '{lexeme.lemma}'.",
        )

    queued_pronunciation_forms = queue_pronunciation_generation(
        runtime,
        stored_lemma=lexeme.lemma,
        requested_forms=added_surface_forms,
    )
    return CompleteVariationsResponse(
        status="updated",
        stored_lemma=lexeme.lemma,
        meaning_id=meaning.id,
        added_surface_forms=added_surface_forms,
        queued_pronunciation_forms=queued_pronunciation_forms,
        queued_verification_targets=[],
        message=_updated_message(lexeme.lemma, added_surface_forms, paradigm_kind=context.paradigm_kind),
    )


def _updated_message(stored_lemma: str, added_surface_forms: list[str], *, paradigm_kind: str) -> str:
    if len(added_surface_forms) == 1:
        return f"Completed {paradigm_kind} variations for '{stored_lemma}' with {added_surface_forms[0]}."
    return f"Completed {paradigm_kind} variations for '{stored_lemma}'."


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


def _complete_variations_gate_message(runtime: WordbankRuntime, *, context) -> str | None:
    meaning_record = runtime.repository.get_verification_record(
        lexeme_id=context.lexeme_id,
        meaning_id=context.meaning_id,
        stored_surface_form=None,
    )
    target_statuses = [meaning_record.status if meaning_record is not None else None]
    for row in runtime.repository.list_surface_forms(context.lexeme_id):
        if row.meaning_id != context.meaning_id:
            continue
        normalized_form = normalize_token(row.form)
        if not normalized_form or normalized_form == context.lemma:
            continue
        record = runtime.repository.get_verification_record(
            lexeme_id=context.lexeme_id,
            meaning_id=context.meaning_id,
            stored_surface_form=normalized_form,
        )
        target_statuses.append(record.status if record is not None else None)

    if any(status == "queued" for status in target_statuses):
        return "Complete variations is unavailable while verification is still running for this meaning."
    if any(status == "error" for status in target_statuses):
        return "Complete variations is unavailable until you retry verification for this meaning."
    if any(status == "flagged" for status in target_statuses):
        return "Complete variations is unavailable until you resolve the verification review for this meaning."
    if not target_statuses or any(status != "verified" for status in target_statuses):
        return "Complete variations is unavailable until this meaning is fully verified."
    return None
