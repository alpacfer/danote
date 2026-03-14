from __future__ import annotations

import json
from datetime import UTC, datetime

from app.api.schemas.v1.wordbank import VerificationAction, VerificationResult
from app.db.repositories.wordbank import WordbankRepository
from app.db.repositories.wordbank_models import VerificationRecord


def now_utc_iso() -> str:
    return datetime.now(UTC).isoformat()


def verification_record_to_schema(record: VerificationRecord) -> VerificationResult:
    return VerificationResult(
        status=record.status,
        provider=record.provider,
        reviewer_role=record.reviewer_role,
        message=record.message,
        composed_word_count=None,
        stored_surface_form=record.stored_surface_form,
        requested_at=record.requested_at,
        completed_at=record.completed_at,
        problem=record.problem,
        change_to_implement=record.change_to_implement,
        suggested_actions=[
            VerificationAction.model_validate(action)
            for action in record.suggested_actions
        ],
    )


def persist_verification_result(
    repository: WordbankRepository,
    *,
    lexeme_id: int,
    meaning_id: int | None,
    stored_surface_form: str | None,
    verification: VerificationResult,
    requested_at: str | None = None,
) -> VerificationRecord:
    existing = repository.get_verification_record(
        lexeme_id=lexeme_id,
        meaning_id=meaning_id,
        stored_surface_form=stored_surface_form,
    )
    return repository.upsert_verification_record(
        lexeme_id=lexeme_id,
        meaning_id=meaning_id,
        status=verification.status,
        provider=verification.provider,
        reviewer_role=verification.reviewer_role,
        stored_surface_form=verification.stored_surface_form,
        message=verification.message,
        problem=verification.problem,
        change_to_implement=verification.change_to_implement,
        suggested_actions=[action.model_dump(exclude_none=True) for action in verification.suggested_actions],
        requested_at=requested_at or existing_requested_at(existing),
        completed_at=verification.completed_at,
    )


def existing_requested_at(record: VerificationRecord | None) -> str:
    return record.requested_at if record is not None else now_utc_iso()


def prune_verification_record_action(
    repository: WordbankRepository,
    *,
    lexeme_id: int,
    meaning_id: int | None,
    stored_surface_form: str | None,
    action: dict[str, object],
) -> None:
    record = repository.get_verification_record(
        lexeme_id=lexeme_id,
        meaning_id=meaning_id,
        stored_surface_form=stored_surface_form,
    )
    if record is None:
        return
    remaining_actions = [
        candidate
        for candidate in record.suggested_actions
        if action_signature(candidate) != action_signature(action)
    ]
    if not remaining_actions:
        repository.delete_verification_record(
            lexeme_id=lexeme_id,
            meaning_id=meaning_id,
            stored_surface_form=stored_surface_form,
        )
        return
    repository.upsert_verification_record(
        lexeme_id=record.lexeme_id,
        meaning_id=record.meaning_id,
        status=record.status,
        provider=record.provider,
        reviewer_role=record.reviewer_role,
        stored_surface_form=record.stored_surface_form,
        message=record.message,
        problem=record.problem,
        change_to_implement=record.change_to_implement,
        suggested_actions=remaining_actions,
        requested_at=record.requested_at,
        completed_at=record.completed_at,
    )


def action_signature(action: dict[str, object]) -> str:
    normalized = {key: value for key, value in action.items() if value is not None}
    return json.dumps(normalized, ensure_ascii=True, sort_keys=True)
