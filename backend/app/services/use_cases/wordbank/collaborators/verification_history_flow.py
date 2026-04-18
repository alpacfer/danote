from __future__ import annotations

import json

from app.api.schemas.v1.wordbank import (
    GetVerificationChangesResponse,
    RevertVerificationChangeResponse,
    VerificationChangeEntry,
)
from app.db.repositories.wordbank import WordbankRepository
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.verification_change_log import (
    revert_fix_translation,
    revert_fix_variations,
)


def get_verification_changes(collaborator, stored_lemma: str) -> GetVerificationChangesResponse:
    normalized_lemma = normalize_token(stored_lemma)
    if not normalized_lemma:
        raise ValueError("stored_lemma is required")
    repository = WordbankRepository(collaborator._db_path)
    records = repository.get_change_log_entries_for_lemma(normalized_lemma)
    items = [
        VerificationChangeEntry(
            id=record.id,
            stored_lemma=record.stored_lemma,
            stored_surface_form=record.stored_surface_form,
            meaning_id=record.meaning_id,
            action_type=record.action_type,
            before_json=json.loads(record.before_json),
            after_json=json.loads(record.after_json),
            applied_at=record.applied_at,
            reverted_at=record.reverted_at,
            provider=record.provider,
        )
        for record in records
    ]
    return GetVerificationChangesResponse(items=items)


def revert_verification_change(
    collaborator,
    change_id: int,
    stored_lemma: str,
) -> RevertVerificationChangeResponse:
    normalized_lemma = normalize_token(stored_lemma)
    if not normalized_lemma:
        raise ValueError("stored_lemma is required")
    repository = WordbankRepository(collaborator._db_path)
    entry = repository.get_change_log_entry(change_id)
    if entry is None or entry.stored_lemma != normalized_lemma:
        return RevertVerificationChangeResponse(status="not_found", change_id=change_id)
    if entry.reverted_at is not None:
        return RevertVerificationChangeResponse(status="already_reverted", change_id=change_id)

    before = json.loads(entry.before_json)
    if entry.action_type == "fix_translation":
        revert_fix_translation(
            db_path=collaborator._db_path,
            stored_lemma=normalized_lemma,
            meaning_id=entry.meaning_id,
            old_translation=before.get("english_translation"),
        )
    elif entry.action_type == "fix_variations":
        revert_fix_variations(
            db_path=collaborator._db_path,
            stored_lemma=normalized_lemma,
            meaning_id=entry.meaning_id,
            surface_forms_snapshot=before.get("surface_forms", []),
        )
    else:
        return RevertVerificationChangeResponse(status="not_found", change_id=change_id)

    collaborator._nlp.invalidate_pos_cache(normalized_lemma, entry.stored_surface_form)
    repository.set_change_log_reverted(change_id, collaborator._now_utc_iso())
    return RevertVerificationChangeResponse(status="reverted", change_id=change_id)
