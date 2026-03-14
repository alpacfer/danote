from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path

from app.api.schemas.v1.wordbank import (
    ApplyVerificationChangesResponse,
    RethinkCategoriesResponse,
    VerificationAction,
    VerificationResult,
    VerifyWordResponse,
)
from app.db.repositories.wordbank import WordbankRepository
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.collaborators.cor import CorResolutionCollaborator
from app.services.use_cases.wordbank.collaborators.nlp import NLPCollaborator
from app.services.use_cases.wordbank.verification_input_builder import build_verification_input
from app.services.use_cases.wordbank.verification_actions import apply_verification_action
from app.services.use_cases.wordbank.verification_apply_resolution import (
    update_persisted_verification_after_apply,
)
from app.services.use_cases.wordbank.verification_categories import (
    persist_category_labels_for_scope,
)
from app.services.use_cases.wordbank.verification_records import (
    now_utc_iso,
    persist_verification_result,
)
from app.services.verification import (
    WordVerificationAction,
    WordVerificationInput,
    WordVerificationService,
)

logger = logging.getLogger(__name__)


class VerificationCollaborator:
    """Handles word verification, applying changes, and the Gemini change log."""

    def __init__(
        self,
        verification_service: WordVerificationService | None,
        db_path: Path,
        gemini_changes_log_path: Path | None,
        nlp: NLPCollaborator,
        cor: CorResolutionCollaborator,
    ) -> None:
        self._verification_service = verification_service
        self._db_path = db_path
        self._gemini_changes_log_path = gemini_changes_log_path
        self._nlp = nlp
        self._cor = cor

    def verify_added_word(
        self,
        stored_lemma: str,
        stored_surface_form: str | None,
        *,
        meaning_id: int | None = None,
    ) -> VerifyWordResponse:
        normalized_lemma = normalize_token(stored_lemma)
        normalized_surface = normalize_token(stored_surface_form or "") or None
        if not normalized_lemma:
            raise ValueError("stored_lemma is required")

        payload = self._build_verification_input(
            stored_lemma=normalized_lemma,
            stored_surface_form=normalized_surface,
            meaning_id=meaning_id,
        )
        verification, category_labels = self._verify_added_word(payload)
        applied_categories = self._persist_verification_result(
            stored_lemma=normalized_lemma,
            meaning_id=meaning_id,
            stored_surface_form=normalized_surface,
            verification=verification,
            category_labels=category_labels,
        )
        return VerifyWordResponse(
            stored_lemma=normalized_lemma,
            stored_surface_form=normalized_surface,
            verification=verification,
            applied_categories=applied_categories,
        )

    def verify_added_word_if_current(
        self,
        stored_lemma: str,
        stored_surface_form: str | None,
        *,
        meaning_id: int | None = None,
        expected_snapshot_hash: str,
    ) -> bool:
        normalized_lemma = normalize_token(stored_lemma)
        normalized_surface = normalize_token(stored_surface_form or "") or None
        if not normalized_lemma:
            raise ValueError("stored_lemma is required")
        payload = self._build_verification_input(
            stored_lemma=normalized_lemma,
            stored_surface_form=normalized_surface,
            meaning_id=meaning_id,
        )
        if self._verification_payload_hash(payload) != expected_snapshot_hash:
            return False
        verification, category_labels = self._verify_added_word(payload)
        self._persist_verification_result(
            stored_lemma=normalized_lemma,
            meaning_id=meaning_id,
            stored_surface_form=normalized_surface,
            verification=verification,
            category_labels=category_labels,
        )
        return True

    def rethink_categories(
        self,
        stored_lemma: str,
        stored_surface_form: str | None,
        *,
        meaning_id: int | None = None,
    ) -> RethinkCategoriesResponse:
        normalized_lemma = normalize_token(stored_lemma)
        normalized_surface = normalize_token(stored_surface_form or "") or None
        if not normalized_lemma:
            raise ValueError("stored_lemma is required")
        payload = self._build_verification_input(
            stored_lemma=normalized_lemma,
            stored_surface_form=normalized_surface,
            meaning_id=meaning_id,
        )
        if self._verification_service is None:
            return RethinkCategoriesResponse(
                status="skipped",
                stored_lemma=normalized_lemma,
                stored_surface_form=normalized_surface,
                meaning_id=meaning_id,
                applied_categories=[],
                message="Word categorization is disabled.",
            )

        try:
            classification = self._verification_service.classify_word_categories(payload)
        except Exception as exc:
            return RethinkCategoriesResponse(
                status="error",
                stored_lemma=normalized_lemma,
                stored_surface_form=normalized_surface,
                meaning_id=meaning_id,
                applied_categories=[],
                message=f"Category rethink failed: {exc}",
            )

        applied_categories = self._persist_categories_for_scope(
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
            message=_rethink_categories_message(normalized_lemma, applied_categories),
        )

    def build_verification_snapshot_hash(
        self,
        *,
        stored_lemma: str,
        stored_surface_form: str | None,
        meaning_id: int | None,
    ) -> str:
        normalized_lemma = normalize_token(stored_lemma)
        normalized_surface = normalize_token(stored_surface_form or "") or None
        if not normalized_lemma:
            raise ValueError("stored_lemma is required")
        payload = self._build_verification_input(
            stored_lemma=normalized_lemma,
            stored_surface_form=normalized_surface,
            meaning_id=meaning_id,
        )
        return self._verification_payload_hash(payload)

    def apply_verification_changes(
        self,
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

        provider_name, reviewer_name = self._verification_metadata(provider_override=provider)
        result = apply_verification_action(
            db_path=self._db_path,
            stored_lemma=normalized_lemma,
            stored_surface_form=normalized_surface,
            meaning_id=meaning_id,
            action=action,
            provider_name=provider_name,
        )
        for lemma, surface in result.invalidate_targets:
            self._nlp.invalidate_pos_cache(lemma, surface)

        if result.log_payload is not None and provider_name == "gemini":
            self._append_gemini_change_log(
                {
                    "timestamp_utc": now_utc_iso(),
                    "provider": provider_name,
                    "stored_lemma": normalized_lemma,
                    "stored_surface_form": normalized_surface,
                    **result.log_payload,
                }
            )

        update_persisted_verification_after_apply(
            db_path=self._db_path,
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

    def queued_verification_result(
        self,
        *,
        stored_surface_form: str | None = None,
        requested_at: str | None = None,
    ) -> VerificationResult:
        if self._verification_service is None:
            return VerificationResult(
                status="skipped",
                provider=None,
                reviewer_role=None,
                message="Word verification is disabled.",
            )
        provider_name, reviewer_name = self._verification_metadata()
        return VerificationResult(
            status="queued",
            provider=provider_name,
            reviewer_role=reviewer_name,
            message="Word verification queued.",
            composed_word_count=None,
            stored_surface_form=stored_surface_form,
            requested_at=requested_at or now_utc_iso(),
        )

    def persist_queued_verification(
        self,
        *,
        stored_lemma: str,
        stored_surface_form: str | None,
        meaning_id: int | None,
        verification: VerificationResult | None,
    ) -> None:
        if verification is None or verification.status != "queued":
            return
        normalized_lemma = normalize_token(stored_lemma)
        if not normalized_lemma:
            return
        repository = WordbankRepository(self._db_path)
        lexeme = repository.get_lexeme(normalized_lemma)
        if lexeme is None:
            return
        persist_verification_result(
            repository,
            lexeme_id=lexeme.id,
            meaning_id=meaning_id,
            stored_surface_form=normalize_token(stored_surface_form or "") or None,
            verification=verification.model_copy(
                update={
                    "stored_surface_form": normalize_token(stored_surface_form or "") or None,
                    "requested_at": verification.requested_at or now_utc_iso(),
                    "completed_at": None,
                }
            ),
            requested_at=verification.requested_at,
        )

    def _append_gemini_change_log(self, payload: dict[str, object]) -> None:
        if self._gemini_changes_log_path is None:
            return
        try:
            self._gemini_changes_log_path.parent.mkdir(parents=True, exist_ok=True)
            with self._gemini_changes_log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=True, sort_keys=True))
                handle.write("\n")
        except Exception:
            logger.exception(
                "wordbank_gemini_change_log_write_failed",
                extra={"gemini_changes_log_path": str(self._gemini_changes_log_path)},
            )

    def _verification_metadata(
        self,
        *,
        provider_override: str | None = None,
    ) -> tuple[str, str | None]:
        provider = provider_override if provider_override is not None else getattr(self._verification_service, "provider", None)
        reviewer_role = getattr(self._verification_service, "reviewer_role", None)
        provider_name = (
            provider.strip().lower()
            if isinstance(provider, str) and provider.strip()
            else "verification"
        )
        reviewer_name = (
            reviewer_role.strip()
            if isinstance(reviewer_role, str) and reviewer_role.strip()
            else None
        )
        return provider_name, reviewer_name

    def _build_verification_input(
        self,
        *,
        stored_lemma: str,
        stored_surface_form: str | None,
        meaning_id: int | None,
    ):
        return build_verification_input(
            db_path=self._db_path,
            nlp=self._nlp,
            cor=self._cor,
            stored_lemma=stored_lemma,
            stored_surface_form=stored_surface_form,
            meaning_id=meaning_id,
        )

    def _verify_added_word(
        self,
        payload: WordVerificationInput,
    ) -> tuple[VerificationResult, list[str]]:
        if self._verification_service is None:
            return (
                VerificationResult(
                    status="skipped",
                    provider=None,
                    reviewer_role=None,
                    message="Word verification is disabled.",
                ),
                [],
            )

        provider_name, reviewer_name = self._verification_metadata()

        try:
            verdict = self._verification_service.verify_word_entry(payload)
        except Exception as exc:
            return (
                VerificationResult(
                    status="error",
                    provider=provider_name,
                    reviewer_role=reviewer_name,
                    message=f"Verification task failed: {exc}",
                    composed_word_count=None,
                    stored_surface_form=payload.stored_surface_form,
                    requested_at=now_utc_iso(),
                    completed_at=now_utc_iso(),
                    problem=str(exc),
                    change_to_implement="Fix Gemini verification setup or provider errors, then run verification again.",
                    suggested_actions=[],
                ),
                [],
            )

        completed_at = now_utc_iso()
        return (
            VerificationResult(
                status=verdict.verdict,
                provider=provider_name,
                reviewer_role=reviewer_name,
                message=verdict.message,
                composed_word_count=getattr(verdict, "composed_word_count", None),
                stored_surface_form=payload.stored_surface_form,
                requested_at=completed_at,
                completed_at=completed_at,
                problem=getattr(verdict, "problem", None),
                change_to_implement=getattr(verdict, "change_to_implement", None),
                suggested_actions=[
                    _verification_action_to_schema(action)
                    for action in getattr(verdict, "suggested_actions", ()) or ()
                ],
            ),
            list(getattr(verdict, "categories", ()) or ()),
        )

    def _persist_verification_result(
        self,
        *,
        stored_lemma: str,
        meaning_id: int | None,
        stored_surface_form: str | None,
        verification: VerificationResult,
        category_labels: list[str],
    ) -> list[str]:
        repository = WordbankRepository(self._db_path)
        lexeme = repository.get_lexeme(stored_lemma)
        if lexeme is None:
            return []
        record = repository.get_verification_record(
            lexeme_id=lexeme.id,
            meaning_id=meaning_id,
            stored_surface_form=stored_surface_form,
        )
        requested_at = record.requested_at if record is not None else verification.requested_at
        persisted = verification.model_copy(
            update={
                "requested_at": requested_at or now_utc_iso(),
                "completed_at": verification.completed_at or (now_utc_iso() if verification.status != "queued" else None),
            }
        )
        record = persist_verification_result(
            repository,
            lexeme_id=lexeme.id,
            meaning_id=meaning_id,
            stored_surface_form=stored_surface_form,
            verification=persisted,
            requested_at=requested_at,
        )
        verification.requested_at = record.requested_at
        verification.completed_at = record.completed_at
        if verification.status not in {"verified", "flagged"}:
            return []
        return self._persist_categories_for_scope(
            stored_lemma=stored_lemma,
            meaning_id=meaning_id,
            labels=category_labels,
        )

    def _persist_categories_for_scope(
        self,
        *,
        stored_lemma: str,
        meaning_id: int | None,
        labels: list[str],
    ) -> list[str]:
        repository = WordbankRepository(self._db_path)
        lexeme = repository.get_lexeme(stored_lemma)
        if lexeme is None:
            raise LookupError(f"Lemma '{stored_lemma}' was not found")
        return persist_category_labels_for_scope(
            repository,
            lexeme_id=lexeme.id,
            meaning_id=meaning_id,
            labels=labels,
        )

    def _verification_payload_hash(self, payload: WordVerificationInput) -> str:
        serialized = {
            key: value
            for key, value in asdict(payload).items()
        }
        return json.dumps(serialized, ensure_ascii=True, sort_keys=True)


def _verification_action_to_schema(action: WordVerificationAction) -> VerificationAction:
    return VerificationAction(
        action_type=action.action_type,
        reason=action.reason,
        english_translation=action.english_translation,
        gloss=action.gloss,
        target_meaning_id=action.target_meaning_id,
        target_lemma=action.target_lemma,
        target_meaning_key=action.target_meaning_key,
        target_gloss=action.target_gloss,
        target_english_translation=action.target_english_translation,
        target_pos_tag=action.target_pos_tag,
        target_morphology=action.target_morphology,
    )


def _rethink_categories_message(stored_lemma: str, applied_categories: list[str]) -> str:
    if not applied_categories:
        return f"Updated categories for '{stored_lemma}'. No categories are currently assigned."
    if len(applied_categories) == 1:
        return f"Updated categories for '{stored_lemma}' to {applied_categories[0]}."
    return f"Updated categories for '{stored_lemma}'."
