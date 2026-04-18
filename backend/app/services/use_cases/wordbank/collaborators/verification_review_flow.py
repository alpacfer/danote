from __future__ import annotations

import logging

from app.api.schemas.v1.wordbank import (
    QueueVerificationResponse,
    RethinkCategoriesResponse,
    VerificationResult,
    VerifyWordResponse,
)
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.verification_helper_logic import (
    normalize_review_intent,
    rethink_categories_message,
)
from app.services.use_cases.wordbank.verification_queue import (
    load_verification_record,
    process_queued_verification_if_current,
)

logger = logging.getLogger(__name__)


def verify_added_word(
    collaborator,
    stored_lemma: str,
    stored_surface_form: str | None,
    *,
    meaning_id: int | None = None,
    review_intent: str = "general",
) -> VerifyWordResponse:
    normalized_lemma = normalize_token(stored_lemma)
    normalized_surface = normalize_token(stored_surface_form or "") or None
    if not normalized_lemma:
        raise ValueError("stored_lemma is required")

    payload = collaborator._build_verification_input(
        stored_lemma=normalized_lemma,
        stored_surface_form=normalized_surface,
        meaning_id=meaning_id,
        review_intent=review_intent,
    )
    verification = collaborator._verify_added_word(payload)
    collaborator._persist_verification_result(
        stored_lemma=normalized_lemma,
        meaning_id=meaning_id,
        stored_surface_form=normalized_surface,
        verification=verification,
        review_intent=normalize_review_intent(review_intent),
        latest_snapshot_hash=collaborator._verification_payload_hash(payload),
    )
    collaborator._auto_apply_eligible_actions(
        stored_lemma=normalized_lemma,
        stored_surface_form=normalized_surface,
        meaning_id=meaning_id,
    )
    applied_categories = collaborator._classify_and_persist_categories(
        stored_lemma=normalized_lemma,
        meaning_id=meaning_id,
        verification=verification,
        payload=payload,
    )
    return VerifyWordResponse(
        stored_lemma=normalized_lemma,
        stored_surface_form=normalized_surface,
        verification=verification,
        applied_categories=applied_categories,
    )


def process_verification_if_current(
    collaborator,
    stored_lemma: str,
    stored_surface_form: str | None,
    *,
    meaning_id: int | None = None,
    expected_snapshot_hash: str,
    expected_generation: int | None = None,
    review_intent: str = "general",
) -> str:
    normalized_review_intent = normalize_review_intent(review_intent)
    result = process_queued_verification_if_current(
        stored_lemma=stored_lemma,
        stored_surface_form=stored_surface_form,
        meaning_id=meaning_id,
        expected_snapshot_hash=expected_snapshot_hash,
        expected_generation=expected_generation,
        review_intent=normalized_review_intent,
        build_input=collaborator._build_verification_input,
        payload_hash=collaborator._verification_payload_hash,
        load_record=lambda lemma, surface, current_meaning_id: load_verification_record(
            db_path=collaborator._db_path,
            stored_lemma=lemma,
            stored_surface_form=surface,
            meaning_id=current_meaning_id,
        ),
        verify_payload=collaborator._verify_added_word,
        persist_result=lambda lemma, current_meaning_id, surface, verification, current_review_intent, snapshot_hash, request_generation: collaborator._persist_verification_result(
            stored_lemma=lemma,
            meaning_id=current_meaning_id,
            stored_surface_form=surface,
            verification=verification,
            review_intent=current_review_intent,
            latest_snapshot_hash=snapshot_hash,
            request_generation=request_generation,
        ),
        classify_and_persist_categories=lambda lemma, current_meaning_id, verification, payload: collaborator._classify_and_persist_categories(
            stored_lemma=lemma,
            meaning_id=current_meaning_id,
            verification=verification,
            payload=payload,
        ),
    )
    if result == "persisted":
        collaborator._auto_apply_eligible_actions(
            stored_lemma=stored_lemma,
            stored_surface_form=stored_surface_form,
            meaning_id=meaning_id,
        )
    return result


def queue_verification_request(
    collaborator,
    stored_lemma: str,
    stored_surface_form: str | None,
    *,
    meaning_id: int | None = None,
    review_intent: str = "general",
    persist: bool = True,
) -> QueueVerificationResponse:
    normalized_lemma = normalize_token(stored_lemma)
    normalized_surface = normalize_token(stored_surface_form or "") or None
    if not normalized_lemma:
        raise ValueError("stored_lemma is required")
    normalized_review_intent = normalize_review_intent(review_intent)
    verification = collaborator.queued_verification_result(stored_surface_form=normalized_surface)
    snapshot_hash = collaborator.build_verification_snapshot_hash(
        stored_lemma=normalized_lemma,
        stored_surface_form=normalized_surface,
        meaning_id=meaning_id,
        review_intent=normalized_review_intent,
    )
    if persist:
        collaborator.persist_queued_verification(
            stored_lemma=normalized_lemma,
            stored_surface_form=normalized_surface,
            meaning_id=meaning_id,
            verification=verification,
            review_intent=normalized_review_intent,
            latest_snapshot_hash=snapshot_hash,
        )
    return QueueVerificationResponse(
        stored_lemma=normalized_lemma,
        stored_surface_form=normalized_surface,
        meaning_id=meaning_id,
        review_intent=normalized_review_intent,
        verification=verification,
    )


def rethink_categories(
    collaborator,
    stored_lemma: str,
    stored_surface_form: str | None,
    *,
    meaning_id: int | None = None,
) -> RethinkCategoriesResponse:
    normalized_lemma = normalize_token(stored_lemma)
    normalized_surface = normalize_token(stored_surface_form or "") or None
    if not normalized_lemma:
        raise ValueError("stored_lemma is required")
    payload = collaborator._build_verification_input(
        stored_lemma=normalized_lemma,
        stored_surface_form=normalized_surface,
        meaning_id=meaning_id,
    )
    if collaborator._verification_service is None:
        return RethinkCategoriesResponse(
            status="skipped",
            stored_lemma=normalized_lemma,
            stored_surface_form=normalized_surface,
            meaning_id=meaning_id,
            applied_categories=[],
            message="Categories disabled.",
        )

    try:
        classification = collaborator._verification_service.classify_word_categories(payload)
    except Exception as exc:
        return RethinkCategoriesResponse(
            status="error",
            stored_lemma=normalized_lemma,
            stored_surface_form=normalized_surface,
            meaning_id=meaning_id,
            applied_categories=[],
            message=f"Category update failed: {exc}",
        )

    applied_categories = collaborator._persist_categories_for_scope(
        stored_lemma=normalized_lemma,
        meaning_id=meaning_id,
        labels=list(getattr(classification, "categories", ()) or ()),
    )
    return RethinkCategoriesResponse(
        status="updated",
        stored_lemma=normalized_lemma,
        stored_surface_form=normalized_surface,
        meaning_id=meaning_id,
        applied_categories=applied_categories,
        message=rethink_categories_message(normalized_lemma, applied_categories),
    )


def build_verification_snapshot_hash(
    collaborator,
    *,
    stored_lemma: str,
    stored_surface_form: str | None,
    meaning_id: int | None,
    review_intent: str = "general",
) -> str:
    normalized_lemma = normalize_token(stored_lemma)
    normalized_surface = normalize_token(stored_surface_form or "") or None
    if not normalized_lemma:
        raise ValueError("stored_lemma is required")
    payload = collaborator._build_verification_input(
        stored_lemma=normalized_lemma,
        stored_surface_form=normalized_surface,
        meaning_id=meaning_id,
        review_intent=review_intent,
    )
    return collaborator._verification_payload_hash(payload)


def verify_word_entries_batch(
    collaborator,
    verification_inputs,
    sentence_context: str | None = None,
) -> list[VerificationResult]:
    if collaborator._verification_service is None:
        return [collaborator._skipped_verification_result(payload) for payload in verification_inputs]

    provider_name, reviewer_name = collaborator._verification_metadata()
    try:
        verdicts = collaborator._verification_service.verify_word_entries_batch(
            verification_inputs,
            sentence_context=sentence_context,
        )
    except Exception as exc:
        logger.warning(
            "wordbank_batch_verification_failed",
            extra={"error": str(exc), "word_count": len(verification_inputs)},
        )
        return [
            collaborator._error_verification_result(payload, exc, provider_name, reviewer_name)
            for payload in verification_inputs
        ]

    completed_at = collaborator._now_utc_iso()
    results: list[VerificationResult] = []
    for payload, verdict in zip(verification_inputs, verdicts, strict=False):
        result = collaborator._build_batch_verification_result(
            verdict,
            payload,
            provider_name,
            reviewer_name,
            completed_at,
        )
        collaborator._persist_batch_result(payload, result)
        results.append(result)

    for payload, result in zip(verification_inputs, results, strict=False):
        if result.status in ("verified", "flagged"):
            collaborator._auto_apply_eligible_actions(
                stored_lemma=payload.stored_lemma,
                stored_surface_form=payload.stored_surface_form,
                meaning_id=payload.meaning_id,
            )
    return results
