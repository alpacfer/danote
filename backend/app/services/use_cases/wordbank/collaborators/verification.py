from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path

from app.api.schemas.v1.wordbank import (
    ApplyVerificationChangesResponse,
    QueueVerificationResponse,
    RethinkCategoriesResponse,
    VerificationResult,
    VerifyWordResponse,
)
from app.db.repositories.wordbank import WordbankRepository
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.collaborators.cor import CorResolutionCollaborator
from app.services.use_cases.wordbank.collaborators.nlp import NLPCollaborator
from app.services.use_cases.wordbank.noun_variations import (
    LEGACY_NOUN_SLOT_ACTION_FIELDS,
    NOUN_SLOT_ACTION_LIST_FIELDS,
    extract_fix_variations_action_slot_form_lists,
    extract_fix_variations_action_slot_forms,
    parse_fix_variations_text_slot_forms,
)
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
from app.services.use_cases.wordbank.verification_queue import (
    load_verification_record,
    persist_queued_verification,
    process_queued_verification_if_current,
    queued_verification_result,
)
from app.services.use_cases.wordbank.verification_helper_logic import (
    completion_review_actions,
    find_fix_variations_action_form_lists,
    find_fix_variations_action_fields,
    normalize_review_intent,
    rethink_categories_message,
    verification_action_to_schema,
)
from app.services.verification import (
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
        review_intent: str = "general",
    ) -> VerifyWordResponse:
        normalized_lemma = normalize_token(stored_lemma)
        normalized_surface = normalize_token(stored_surface_form or "") or None
        if not normalized_lemma:
            raise ValueError("stored_lemma is required")

        payload = self._build_verification_input(
            stored_lemma=normalized_lemma,
            stored_surface_form=normalized_surface,
            meaning_id=meaning_id,
            review_intent=review_intent,
        )
        verification, category_labels = self._verify_added_word(payload)
        applied_categories = self._persist_verification_result(
            stored_lemma=normalized_lemma,
            meaning_id=meaning_id,
            stored_surface_form=normalized_surface,
            verification=verification,
            category_labels=category_labels,
            review_intent=normalize_review_intent(review_intent),
            latest_snapshot_hash=self._verification_payload_hash(payload),
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
        expected_generation: int | None = None,
        review_intent: str = "general",
    ) -> bool:
        return (
            self.process_queued_verification_if_current(
                stored_lemma,
                stored_surface_form,
                meaning_id=meaning_id,
                expected_snapshot_hash=expected_snapshot_hash,
                expected_generation=expected_generation,
                review_intent=review_intent,
            )
            == "persisted"
        )

    def process_queued_verification_if_current(
        self,
        stored_lemma: str,
        stored_surface_form: str | None,
        *,
        meaning_id: int | None = None,
        expected_snapshot_hash: str,
        expected_generation: int | None = None,
        review_intent: str = "general",
    ) -> str:
        normalized_review_intent = normalize_review_intent(review_intent)
        return process_queued_verification_if_current(
            stored_lemma=stored_lemma,
            stored_surface_form=stored_surface_form,
            meaning_id=meaning_id,
            expected_snapshot_hash=expected_snapshot_hash,
            expected_generation=expected_generation,
            review_intent=normalized_review_intent,
            build_input=self._build_verification_input,
            payload_hash=self._verification_payload_hash,
            load_record=lambda lemma, surface, current_meaning_id: load_verification_record(
                db_path=self._db_path,
                stored_lemma=lemma,
                stored_surface_form=surface,
                meaning_id=current_meaning_id,
            ),
            verify_payload=self._verify_added_word,
            persist_result=lambda lemma, current_meaning_id, surface, verification, labels, current_review_intent, snapshot_hash, request_generation: self._persist_verification_result(
                stored_lemma=lemma,
                meaning_id=current_meaning_id,
                stored_surface_form=surface,
                verification=verification,
                category_labels=labels,
                review_intent=current_review_intent,
                latest_snapshot_hash=snapshot_hash,
                request_generation=request_generation,
            ),
        )

    def queue_verification_request(
        self,
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
        verification = self.queued_verification_result(stored_surface_form=normalized_surface)
        snapshot_hash = self.build_verification_snapshot_hash(
            stored_lemma=normalized_lemma,
            stored_surface_form=normalized_surface,
            meaning_id=meaning_id,
            review_intent=normalized_review_intent,
        )
        if persist:
            self.persist_queued_verification(
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
            message=rethink_categories_message(normalized_lemma, applied_categories),
        )

    def build_verification_snapshot_hash(
        self,
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
        payload = self._build_verification_input(
            stored_lemma=normalized_lemma,
            stored_surface_form=normalized_surface,
            meaning_id=meaning_id,
            review_intent=review_intent,
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
        self._assert_apply_action_allowed(
            stored_lemma=normalized_lemma,
            stored_surface_form=normalized_surface,
            meaning_id=meaning_id,
            action=action,
        )
        resolved_action = self._resolve_apply_action(
            stored_lemma=normalized_lemma,
            stored_surface_form=normalized_surface,
            meaning_id=meaning_id,
            action=action,
        )
        result = apply_verification_action(
            db_path=self._db_path,
            cor=self._cor,
            stored_lemma=normalized_lemma,
            stored_surface_form=normalized_surface,
            meaning_id=meaning_id,
            action=resolved_action,
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

    def _resolve_apply_action(
        self,
        *,
        stored_lemma: str,
        stored_surface_form: str | None,
        meaning_id: int | None,
        action: dict[str, object],
    ) -> dict[str, object]:
        if action.get("action_type") != "fix_variations":
            return action
        if (
            extract_fix_variations_action_slot_form_lists(action)
            or extract_fix_variations_action_slot_forms(action)
        ):
            return action

        repository = WordbankRepository(self._db_path)
        lexeme = repository.get_lexeme(stored_lemma)
        if lexeme is None:
            return action
        record = repository.get_verification_record(
            lexeme_id=lexeme.id,
            meaning_id=meaning_id,
            stored_surface_form=stored_surface_form,
        )
        if record is None:
            return action

        hydrated_form_lists = find_fix_variations_action_form_lists(record.suggested_actions)
        if hydrated_form_lists:
            return {
                **action,
                **{
                    field_name: form_list
                    for slot_name, form_list in hydrated_form_lists.items()
                    if (field_name := NOUN_SLOT_ACTION_LIST_FIELDS.get(slot_name)) is not None
                },
            }

        hydrated_fields = find_fix_variations_action_fields(record.suggested_actions)
        if not hydrated_fields:
            hydrated_fields = parse_fix_variations_text_slot_forms(record.change_to_implement)
        if not hydrated_fields:
            hydrated_fields = parse_fix_variations_text_slot_forms(record.problem)
        if not hydrated_fields:
            return action
        return {
            **action,
            **{
                field_name: form
                for slot_name, form in hydrated_fields.items()
                if (field_name := LEGACY_NOUN_SLOT_ACTION_FIELDS.get(slot_name)) is not None
            },
        }

    def _assert_apply_action_allowed(
        self,
        *,
        stored_lemma: str,
        stored_surface_form: str | None,
        meaning_id: int | None,
        action: dict[str, object],
    ) -> None:
        repository = WordbankRepository(self._db_path)
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

    def queued_verification_result(
        self,
        *,
        stored_surface_form: str | None = None,
        requested_at: str | None = None,
        review_intent: str = "general",
    ) -> VerificationResult:
        return queued_verification_result(
            verification_enabled=self._verification_service is not None,
            metadata_provider=self._verification_metadata,
            stored_surface_form=stored_surface_form,
            requested_at=requested_at,
            review_intent=normalize_review_intent(review_intent),
        )

    def persist_queued_verification(
        self,
        *,
        stored_lemma: str,
        stored_surface_form: str | None,
        meaning_id: int | None,
        verification: VerificationResult | None,
        review_intent: str = "general",
        latest_snapshot_hash: str | None = None,
    ) -> int | None:
        return persist_queued_verification(
            db_path=self._db_path,
            stored_lemma=stored_lemma,
            stored_surface_form=stored_surface_form,
            meaning_id=meaning_id,
            verification=verification,
            review_intent=normalize_review_intent(review_intent),
            latest_snapshot_hash=latest_snapshot_hash,
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
        review_intent: str = "general",
    ):
        return build_verification_input(
            db_path=self._db_path,
            nlp=self._nlp,
            cor=self._cor,
            stored_lemma=stored_lemma,
            stored_surface_form=stored_surface_form,
            meaning_id=meaning_id,
            review_intent=normalize_review_intent(review_intent),
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
                    review_intent=payload.review_intent,
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
                    review_intent=payload.review_intent,
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
        suggested_actions = [
            verification_action_to_schema(action)
            for action in getattr(verdict, "suggested_actions", ()) or ()
        ]
        if (
            payload.review_intent != "complete_variations"
            and verdict.verdict == "flagged"
            and suggested_actions
            and all(action.action_type == "fix_variations" for action in suggested_actions)
        ):
            return (
                VerificationResult(
                    status="verified",
                    provider=provider_name,
                    reviewer_role=reviewer_name,
                    review_intent=payload.review_intent,
                    message="OK",
                    composed_word_count=getattr(verdict, "composed_word_count", None),
                    stored_surface_form=payload.stored_surface_form,
                    requested_at=completed_at,
                    completed_at=completed_at,
                    suggested_actions=[],
                ),
                list(getattr(verdict, "categories", ()) or ()),
            )
        suggested_actions = completion_review_actions(
            payload=payload,
            verification_status=verdict.verdict,
            suggested_actions=suggested_actions,
            problem=getattr(verdict, "problem", None),
            change_to_implement=getattr(verdict, "change_to_implement", None),
        )
        return (
            VerificationResult(
                status=verdict.verdict,
                provider=provider_name,
                reviewer_role=reviewer_name,
                review_intent=payload.review_intent,
                message=verdict.message,
                composed_word_count=getattr(verdict, "composed_word_count", None),
                stored_surface_form=payload.stored_surface_form,
                requested_at=completed_at,
                completed_at=completed_at,
                problem=getattr(verdict, "problem", None),
                change_to_implement=getattr(verdict, "change_to_implement", None),
                suggested_actions=suggested_actions,
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
        review_intent: str | None = None,
        latest_snapshot_hash: str | None = None,
        request_generation: int | None = None,
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
            review_intent=review_intent,
            latest_snapshot_hash=latest_snapshot_hash,
            request_generation=request_generation,
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
