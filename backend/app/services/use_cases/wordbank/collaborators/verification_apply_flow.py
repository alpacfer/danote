from __future__ import annotations

from app.api.schemas.v1.wordbank import ApplyVerificationChangesResponse
from app.db.repositories.wordbank import WordbankRepository
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.verification_apply_resolution import (
    update_persisted_verification_after_apply,
)
from app.services.use_cases.wordbank.verification_change_log import (
    query_surface_forms_snapshot,
)
from app.services.use_cases.wordbank.verification_actions import apply_verification_action


def apply_verification_changes(
    collaborator,
    *,
    stored_lemma: str,
    stored_surface_form: str | None,
    meaning_id: int | None,
    action: dict[str, object],
    provider: str | None = None,
) -> ApplyVerificationChangesResponse:
    normalized_lemma = normalize_token(stored_lemma)
    normalized_surface = normalize_token(stored_surface_form or "") or None
    if not normalized_lemma:
        raise ValueError("stored_lemma is required")

    provider_name, reviewer_name = collaborator._verification_metadata(provider_override=provider)
    assert_apply_action_allowed(
        collaborator,
        stored_lemma=normalized_lemma,
        stored_surface_form=normalized_surface,
        meaning_id=meaning_id,
        action=action,
    )
    action_type_str = str(action.get("action_type", ""))
    pre_apply_surfaces: list[dict[str, object]] | None = None
    if action_type_str == "fix_variations":
        repository = WordbankRepository(collaborator._db_path)
        lexeme = repository.get_lexeme(normalized_lemma)
        if lexeme is not None:
            pre_apply_surfaces = query_surface_forms_snapshot(
                collaborator._db_path,
                lexeme_id=lexeme.id,
                meaning_id=meaning_id,
            )

    result = apply_verification_action(
        db_path=collaborator._db_path,
        cor=collaborator._cor,
        stored_lemma=normalized_lemma,
        stored_surface_form=normalized_surface,
        meaning_id=meaning_id,
        action=action,
        provider_name=provider_name,
    )
    for lemma, surface in result.invalidate_targets:
        collaborator._nlp.invalidate_pos_cache(lemma, surface)

    if result.log_payload is not None and provider_name == "gemini":
        collaborator._append_gemini_change_log(
            {
                "timestamp_utc": collaborator._now_utc_iso(),
                "provider": provider_name,
                "stored_lemma": normalized_lemma,
                "stored_surface_form": normalized_surface,
                **result.log_payload,
            }
        )

    collaborator._write_change_log_db_entry(
        stored_lemma=normalized_lemma,
        stored_surface_form=normalized_surface,
        meaning_id=meaning_id,
        result=result,
        pre_apply_surfaces=pre_apply_surfaces,
        provider_name=provider_name,
        applied_at=collaborator._now_utc_iso(),
    )

    update_persisted_verification_after_apply(
        db_path=collaborator._db_path,
        status=result.status,
        stored_lemma=normalized_lemma,
        stored_surface_form=normalized_surface,
        meaning_id=meaning_id,
        action=action,
        applied_action_type=result.applied_action_type,
        target_lemma=result.target_lemma,
        target_meaning_id=result.target_meaning_id,
        provider_name=provider_name,
        reviewer_name=reviewer_name,
    )

    return ApplyVerificationChangesResponse(
        status=result.status,
        stored_lemma=normalized_lemma,
        stored_surface_form=normalized_surface,
        applied_action_type=result.applied_action_type,
        target_lemma=result.target_lemma,
        target_meaning_id=result.target_meaning_id,
    )


def assert_apply_action_allowed(
    collaborator,
    *,
    stored_lemma: str,
    stored_surface_form: str | None,
    meaning_id: int | None,
    action: dict[str, object],
) -> None:
    if stored_surface_form is not None and action.get("action_type") == "fix_translation":
        raise ValueError("fix_translation cannot be applied for surface-form verification targets.")
    repository = WordbankRepository(collaborator._db_path)
    lexeme = repository.get_lexeme(stored_lemma)
    if lexeme is None:
        return
    record = repository.get_verification_record(
        lexeme_id=lexeme.id,
        meaning_id=meaning_id,
        stored_surface_form=stored_surface_form,
    )
    if record is None or record.review_intent != "complete_variations":
        return
    if action.get("action_type") == "fix_variations":
        return
    raise ValueError("Only fix_variations can be applied for complete-variations reviews.")
