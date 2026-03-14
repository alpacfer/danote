from __future__ import annotations

from pathlib import Path

from app.api.schemas.v1.wordbank import VerificationResult
from app.db.repositories.wordbank import WordbankRepository
from app.db.repositories.wordbank_models import VerificationRecord
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.verification_records import (
    now_utc_iso,
    persist_verification_result,
    prune_verification_record_action,
)


def update_persisted_verification_after_apply(
    *,
    db_path: Path,
    status: str,
    stored_lemma: str,
    stored_surface_form: str | None,
    meaning_id: int | None,
    action: dict[str, object],
    applied_action_type: str | None,
    target_lemma: str | None,
    target_meaning_id: int | None,
    provider_name: str,
    reviewer_name: str | None,
) -> None:
    if status != "applied":
        return
    repository = WordbankRepository(db_path)
    lexeme = repository.get_lexeme(stored_lemma)
    if lexeme is None:
        return
    source_record = repository.get_verification_record(
        lexeme_id=lexeme.id,
        meaning_id=meaning_id,
        stored_surface_form=stored_surface_form,
    )
    provider = source_record.provider if source_record is not None else provider_name
    reviewer = source_record.reviewer_role if source_record is not None else reviewer_name

    if applied_action_type in {"move_to_meaning_section", "move_to_lemma"}:
        repository.delete_verification_record(
            lexeme_id=lexeme.id,
            meaning_id=meaning_id,
            stored_surface_form=stored_surface_form,
        )
        persist_verified_after_apply(
            repository,
            target_lemma=target_lemma or stored_lemma,
            target_meaning_id=target_meaning_id,
            target_stored_surface_form=resolved_target_surface_form(
                applied_action_type=applied_action_type,
                stored_lemma=stored_lemma,
                stored_surface_form=stored_surface_form,
                target_lemma=target_lemma,
            ),
            source_record=source_record,
            provider_name=provider,
            reviewer_name=reviewer,
        )
        return

    if target_lemma is not None and target_lemma != stored_lemma:
        repository.delete_verification_record(
            lexeme_id=lexeme.id,
            meaning_id=meaning_id,
            stored_surface_form=stored_surface_form,
        )
        persist_verified_after_apply(
            repository,
            target_lemma=target_lemma,
            target_meaning_id=target_meaning_id,
            target_stored_surface_form=stored_surface_form,
            source_record=source_record,
            provider_name=provider,
            reviewer_name=reviewer,
        )
        return

    if (target_meaning_id if target_meaning_id is not None else None) != (meaning_id if meaning_id is not None else None):
        repository.delete_verification_record(
            lexeme_id=lexeme.id,
            meaning_id=meaning_id,
            stored_surface_form=stored_surface_form,
        )
        persist_verified_after_apply(
            repository,
            target_lemma=stored_lemma,
            target_meaning_id=target_meaning_id,
            target_stored_surface_form=stored_surface_form,
            source_record=source_record,
            provider_name=provider,
            reviewer_name=reviewer,
        )
        return

    prune_verification_record_action(
        repository,
        lexeme_id=lexeme.id,
        meaning_id=meaning_id,
        stored_surface_form=stored_surface_form,
        action=action,
    )
    if repository.get_verification_record(
        lexeme_id=lexeme.id,
        meaning_id=meaning_id,
        stored_surface_form=stored_surface_form,
    ) is None:
        persist_verified_after_apply(
            repository,
            target_lemma=stored_lemma,
            target_meaning_id=meaning_id,
            target_stored_surface_form=stored_surface_form,
            source_record=source_record,
            provider_name=provider,
            reviewer_name=reviewer,
        )


def persist_verified_after_apply(
    repository: WordbankRepository,
    *,
    target_lemma: str,
    target_meaning_id: int | None,
    target_stored_surface_form: str | None,
    source_record: VerificationRecord | None,
    provider_name: str | None,
    reviewer_name: str | None,
) -> None:
    normalized_target_lemma = normalize_token(target_lemma)
    normalized_target_surface = normalize_token(target_stored_surface_form or "") or None
    if not normalized_target_lemma:
        return
    target_lexeme = repository.get_lexeme(normalized_target_lemma)
    if target_lexeme is None:
        return
    target_record = repository.get_verification_record(
        lexeme_id=target_lexeme.id,
        meaning_id=target_meaning_id,
        stored_surface_form=normalized_target_surface,
    )
    if (
        target_record is not None
        and source_record is not None
        and target_record.id != source_record.id
        and (target_record.suggested_actions or target_record.status in {"queued", "flagged", "error"})
    ):
        return
    requested_at = target_record.requested_at if target_record is not None else None
    provider = target_record.provider if target_record is not None else None
    reviewer_role = target_record.reviewer_role if target_record is not None else None
    if source_record is not None:
        requested_at = requested_at or source_record.requested_at
        provider = provider or source_record.provider
        reviewer_role = reviewer_role or source_record.reviewer_role
    verification = VerificationResult(
        status="verified",
        provider=provider or provider_name,
        reviewer_role=reviewer_role or reviewer_name,
        message="Verification passed.",
        stored_surface_form=normalized_target_surface,
        requested_at=requested_at or now_utc_iso(),
        completed_at=now_utc_iso(),
        suggested_actions=[],
    )
    persist_verification_result(
        repository,
        lexeme_id=target_lexeme.id,
        meaning_id=target_meaning_id,
        stored_surface_form=normalized_target_surface,
        verification=verification,
        requested_at=requested_at,
    )


def resolved_target_surface_form(
    *,
    applied_action_type: str | None,
    stored_lemma: str,
    stored_surface_form: str | None,
    target_lemma: str | None,
) -> str | None:
    if applied_action_type != "move_to_lemma":
        return stored_surface_form
    normalized_surface = normalize_token(stored_surface_form or "") or None
    normalized_stored_lemma = normalize_token(stored_lemma)
    normalized_target_lemma = normalize_token(target_lemma or "") or None
    if normalized_surface is None:
        return None
    if normalized_surface != normalized_stored_lemma:
        return normalized_surface
    return normalized_target_lemma
