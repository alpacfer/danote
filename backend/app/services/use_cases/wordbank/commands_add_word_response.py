from __future__ import annotations

from typing import Literal

from app.api.schemas.v1.wordbank import AddWordResponse, MeaningContext, VerificationResult
from app.services.use_cases.wordbank.queries_details import get_lemma_details


def build_add_word_response(
    *,
    runtime,
    inputs,
    write_result,
    meaning,
    verification: VerificationResult | None,
    queued_verification_targets,
    queued_pronunciation_forms: list[str],
    pronunciation,
) -> AddWordResponse:
    status: Literal["inserted", "exists"] = "inserted" if write_result.inserted_any else "exists"
    message = (
        f"Added '{inputs.stored_lemma}' to wordbank."
        if write_result.inserted_any
        else f"'{inputs.stored_lemma}' is already in the wordbank."
    )
    saved_snapshot = get_lemma_details(runtime, inputs.stored_lemma)
    return AddWordResponse(
        status=status,
        stored_lemma=inputs.stored_lemma,
        stored_surface_form=inputs.normalized_surface or None,
        source="manual",
        message=message,
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
        queued_pronunciation_forms=queued_pronunciation_forms,
        pronunciation=pronunciation,
        saved_snapshot=saved_snapshot,
    )
