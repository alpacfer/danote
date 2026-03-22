from __future__ import annotations

from collections.abc import Callable

from app.api.schemas.v1.wordbank import VerificationResult
from app.db.repositories.wordbank import VerificationRecord, WordbankRepository
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.verification_records import now_utc_iso, persist_verification_result


def queued_verification_result(
    *,
    verification_enabled: bool,
    metadata_provider: Callable[[], tuple[str, str | None]],
    stored_surface_form: str | None = None,
    requested_at: str | None = None,
    review_intent: str = "general",
) -> VerificationResult:
    if not verification_enabled:
        return VerificationResult(
            status="skipped",
            provider=None,
            reviewer_role=None,
            review_intent=review_intent,
            message="Verification disabled.",
        )
    provider_name, reviewer_name = metadata_provider()
    return VerificationResult(
        status="queued",
        provider=provider_name,
        reviewer_role=reviewer_name,
        review_intent=review_intent,
        message="Queued",
        composed_word_count=None,
        stored_surface_form=stored_surface_form,
        requested_at=requested_at or now_utc_iso(),
    )


def persist_queued_verification(
    *,
    db_path,
    stored_lemma: str,
    stored_surface_form: str | None,
    meaning_id: int | None,
    verification: VerificationResult | None,
    review_intent: str = "general",
    latest_snapshot_hash: str | None = None,
) -> int | None:
    if verification is None or verification.status != "queued":
        return None
    normalized_lemma = normalize_token(stored_lemma)
    if not normalized_lemma:
        return None
    repository = WordbankRepository(db_path)
    lexeme = repository.get_lexeme(normalized_lemma)
    if lexeme is None:
        return None
    normalized_surface = normalize_token(stored_surface_form or "") or None
    existing = repository.get_verification_record(
        lexeme_id=lexeme.id,
        meaning_id=meaning_id,
        stored_surface_form=normalized_surface,
    )
    request_generation = (existing.request_generation if existing is not None else 0) + 1
    record = persist_verification_result(
        repository,
        lexeme_id=lexeme.id,
        meaning_id=meaning_id,
        stored_surface_form=normalized_surface,
        verification=verification.model_copy(
            update={
                "stored_surface_form": normalized_surface,
                "requested_at": verification.requested_at or now_utc_iso(),
                "completed_at": None,
            }
        ),
        requested_at=verification.requested_at,
        review_intent=review_intent,
        latest_snapshot_hash=latest_snapshot_hash,
        request_generation=request_generation,
    )
    verification.requested_at = record.requested_at
    verification.completed_at = record.completed_at
    return record.request_generation


def process_queued_verification_if_current(
    *,
    stored_lemma: str,
    stored_surface_form: str | None,
    meaning_id: int | None,
    expected_snapshot_hash: str,
    expected_generation: int | None,
    review_intent: str,
    build_input: Callable[..., object],
    payload_hash: Callable[[object], str],
    load_record: Callable[[str, str | None, int | None], VerificationRecord | None],
    verify_payload: Callable[[object], VerificationResult],
    persist_result: Callable[[str, int | None, str | None, VerificationResult, str, str, int | None], object],
    classify_and_persist_categories: Callable[[str, int | None, VerificationResult, object], list[str]],
) -> str:
    normalized_lemma = normalize_token(stored_lemma)
    normalized_surface = normalize_token(stored_surface_form or "") or None
    if not normalized_lemma:
        raise ValueError("stored_lemma is required")

    payload = build_input(
        stored_lemma=normalized_lemma,
        stored_surface_form=normalized_surface,
        meaning_id=meaning_id,
        review_intent=review_intent,
    )
    if payload_hash(payload) != expected_snapshot_hash:
        return "stale"

    current_record = load_record(normalized_lemma, normalized_surface, meaning_id)
    if not matches_current_request(
        record=current_record,
        expected_snapshot_hash=expected_snapshot_hash,
        expected_generation=expected_generation,
        review_intent=review_intent,
    ):
        return "stale"

    verification = verify_payload(payload)
    current_record = load_record(normalized_lemma, normalized_surface, meaning_id)
    if not matches_current_request(
        record=current_record,
        expected_snapshot_hash=expected_snapshot_hash,
        expected_generation=expected_generation,
        review_intent=review_intent,
    ):
        return "stale"

    persist_result(
        normalized_lemma,
        meaning_id,
        normalized_surface,
        verification,
        review_intent,
        expected_snapshot_hash,
        current_record.request_generation if current_record is not None else expected_generation,
    )
    current_record = load_record(normalized_lemma, normalized_surface, meaning_id)
    if not matches_current_request(
        record=current_record,
        expected_snapshot_hash=expected_snapshot_hash,
        expected_generation=expected_generation,
        review_intent=review_intent,
    ):
        return "stale"
    classify_and_persist_categories(
        normalized_lemma,
        meaning_id,
        verification,
        payload,
    )
    return "persisted"


def load_verification_record(
    *,
    db_path,
    stored_lemma: str,
    stored_surface_form: str | None,
    meaning_id: int | None,
) -> VerificationRecord | None:
    repository = WordbankRepository(db_path)
    lexeme = repository.get_lexeme(stored_lemma)
    if lexeme is None:
        return None
    return repository.get_verification_record(
        lexeme_id=lexeme.id,
        meaning_id=meaning_id,
        stored_surface_form=stored_surface_form,
    )


def matches_current_request(
    *,
    record: VerificationRecord | None,
    expected_snapshot_hash: str,
    expected_generation: int | None,
    review_intent: str,
) -> bool:
    if record is None:
        return False
    if record.review_intent != review_intent:
        return False
    if record.latest_snapshot_hash != expected_snapshot_hash:
        return False
    if expected_generation is not None and record.request_generation != expected_generation:
        return False
    return True
