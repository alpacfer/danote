from __future__ import annotations

import json
import logging
from pathlib import Path

from app.api.schemas.v1.wordbank import (
    ApplyVerificationChangesResponse,
    VerificationAction,
    VerificationResult,
    VerifyWordResponse,
)
from app.db.repositories.wordbank import WordbankRepository
from app.db.migrations import get_connection
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.collaborators.nlp import NLPCollaborator
from app.services.use_cases.wordbank.verification_actions import apply_verification_action
from app.services.use_cases.wordbank.verification_records import (
    now_utc_iso,
    persist_verification_result,
    prune_verification_record_action,
)
from app.services.verification import (
    WordVerificationAction,
    WordVerificationInput,
    WordVerificationMeaningSection,
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
    ) -> None:
        self._verification_service = verification_service
        self._db_path = db_path
        self._gemini_changes_log_path = gemini_changes_log_path
        self._nlp = nlp

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
        verification = self._verify_added_word(payload)
        self._persist_verification_result(
            stored_lemma=normalized_lemma,
            meaning_id=meaning_id,
            verification=verification,
        )
        return VerifyWordResponse(
            stored_lemma=normalized_lemma,
            stored_surface_form=normalized_surface,
            verification=verification,
        )

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

        provider_name, _ = self._verification_metadata(provider_override=provider)
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

        self._update_persisted_verification_after_apply(
            stored_lemma=normalized_lemma,
            meaning_id=meaning_id,
            action=action,
            applied_action_type=result.applied_action_type,
            target_lemma=result.target_lemma,
            target_meaning_id=result.target_meaning_id,
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
    ) -> WordVerificationInput:
        lexeme_source = "manual"
        lexeme_translation: str | None = None
        lexeme_translation_provider: str | None = None
        surface_source: str | None = None
        meaning_key: str | None = None
        meaning_gloss: str | None = None
        sibling_meaning_sections: list[WordVerificationMeaningSection] = []

        with get_connection(self._db_path) as conn:
            lexeme_row = conn.execute(
                """
                SELECT id, source, english_translation, translation_provider
                FROM lexemes
                WHERE lemma = ?
                LIMIT 1
                """,
                (stored_lemma,),
            ).fetchone()

            if lexeme_row is not None:
                lexeme_source = lexeme_row["source"]
                meaning_rows = conn.execute(
                    """
                    SELECT id, meaning_key, gloss, english_translation, pos_tag, morphology
                    FROM lexeme_meanings
                    WHERE lexeme_id = ?
                    ORDER BY id ASC
                    """,
                    (int(lexeme_row["id"]),),
                ).fetchall()
                surface_rows = conn.execute(
                    """
                    SELECT form, meaning_id
                    FROM surface_forms
                    WHERE lexeme_id = ?
                    ORDER BY id ASC
                    """,
                    (int(lexeme_row["id"]),),
                ).fetchall()
                forms_by_meaning: dict[int, list[str]] = {}
                for row in surface_rows:
                    if row["meaning_id"] is None:
                        continue
                    forms_by_meaning.setdefault(int(row["meaning_id"]), []).append(str(row["form"]))

                meaning_row = self._load_meaning_row(
                    conn,
                    lexeme_id=int(lexeme_row["id"]),
                    requested_meaning_id=meaning_id,
                    normalized_lemma=stored_lemma,
                )
                if meaning_row is not None:
                    lexeme_translation = meaning_row["english_translation"]
                    lexeme_translation_provider = "meaning_section"
                    meaning_key = meaning_row["meaning_key"]
                    meaning_gloss = meaning_row["gloss"]
                else:
                    lexeme_translation = lexeme_row["english_translation"]
                    lexeme_translation_provider = lexeme_row["translation_provider"]

                sibling_meaning_sections = [
                    WordVerificationMeaningSection(
                        id=int(row["id"]),
                        meaning_key=str(row["meaning_key"]),
                        gloss=row["gloss"],
                        english_translation=row["english_translation"],
                        pos_tag=row["pos_tag"],
                        morphology=row["morphology"],
                        surface_forms=tuple(forms_by_meaning.get(int(row["id"]), [])),
                    )
                    for row in meaning_rows
                ]

                if stored_surface_form:
                    if meaning_id is not None:
                        surface_row = conn.execute(
                            """
                            SELECT source
                            FROM surface_forms
                            WHERE meaning_id = ? AND form = ?
                            LIMIT 1
                            """,
                            (meaning_id, stored_surface_form),
                        ).fetchone()
                    else:
                        surface_row = conn.execute(
                            """
                            SELECT source
                            FROM surface_forms
                            WHERE lexeme_id = ? AND meaning_id IS NULL AND form = ?
                            LIMIT 1
                            """,
                            (lexeme_row["id"], stored_surface_form),
                        ).fetchone()
                    if surface_row is not None:
                        surface_source = surface_row["source"]

        lemma_pos_tag, lemma_morphology = self._nlp.extract_pos_and_morphology(stored_lemma)
        surface_pos_tag: str | None = None
        surface_morphology: str | None = None
        if stored_surface_form:
            surface_pos_tag, surface_morphology = self._nlp.extract_pos_and_morphology(stored_surface_form)

        return WordVerificationInput(
            stored_lemma=stored_lemma,
            stored_surface_form=stored_surface_form,
            meaning_id=meaning_id,
            meaning_key=meaning_key,
            meaning_gloss=meaning_gloss,
            lexeme_source=lexeme_source,
            lexeme_translation=lexeme_translation,
            lexeme_translation_provider=lexeme_translation_provider,
            surface_source=surface_source,
            lemma_pos_tag=lemma_pos_tag,
            lemma_morphology=lemma_morphology,
            surface_pos_tag=surface_pos_tag,
            surface_morphology=surface_morphology,
            sibling_meaning_sections=tuple(sibling_meaning_sections),
        )

    def _load_meaning_row(
        self,
        conn,
        *,
        lexeme_id: int,
        requested_meaning_id: int | None,
        normalized_lemma: str,
    ):
        if requested_meaning_id is not None:
            meaning_row = conn.execute(
                """
                SELECT id, meaning_key, gloss, english_translation, pos_tag, morphology
                FROM lexeme_meanings
                WHERE id = ? AND lexeme_id = ?
                LIMIT 1
                """,
                (requested_meaning_id, lexeme_id),
            ).fetchone()
            if meaning_row is None:
                raise LookupError(f"Meaning '{requested_meaning_id}' was not found for '{normalized_lemma}'")
            return meaning_row

        meaning_rows = conn.execute(
            """
            SELECT id, meaning_key, gloss, english_translation, pos_tag, morphology
            FROM lexeme_meanings
            WHERE lexeme_id = ?
            ORDER BY id ASC
            LIMIT 2
            """,
            (lexeme_id,),
        ).fetchall()
        if len(meaning_rows) == 1:
            return meaning_rows[0]
        return None

    def _verify_added_word(
        self,
        payload: WordVerificationInput,
    ) -> VerificationResult:
        if self._verification_service is None:
            return VerificationResult(
                status="skipped",
                provider=None,
                reviewer_role=None,
                message="Word verification is disabled.",
            )

        provider_name, reviewer_name = self._verification_metadata()

        try:
            verdict = self._verification_service.verify_word_entry(payload)
        except Exception as exc:
            return VerificationResult(
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
            )

        completed_at = now_utc_iso()
        return VerificationResult(
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
        )

    def _persist_verification_result(
        self,
        *,
        stored_lemma: str,
        meaning_id: int | None,
        verification: VerificationResult,
    ) -> None:
        repository = WordbankRepository(self._db_path)
        lexeme = repository.get_lexeme(stored_lemma)
        if lexeme is None:
            return
        record = repository.get_verification_record(lexeme_id=lexeme.id, meaning_id=meaning_id)
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
            verification=persisted,
            requested_at=requested_at,
        )
        verification.requested_at = record.requested_at
        verification.completed_at = record.completed_at

    def _update_persisted_verification_after_apply(
        self,
        *,
        stored_lemma: str,
        meaning_id: int | None,
        action: dict[str, object],
        applied_action_type: str | None,
        target_lemma: str | None,
        target_meaning_id: int | None,
    ) -> None:
        repository = WordbankRepository(self._db_path)
        lexeme = repository.get_lexeme(stored_lemma)
        if lexeme is None:
            return
        if applied_action_type in {"move_to_meaning_section", "move_to_lemma"}:
            repository.delete_verification_record(lexeme_id=lexeme.id, meaning_id=meaning_id)
            return
        if target_lemma is not None and target_lemma != stored_lemma:
            repository.delete_verification_record(lexeme_id=lexeme.id, meaning_id=meaning_id)
            return
        if (target_meaning_id if target_meaning_id is not None else None) != (meaning_id if meaning_id is not None else None):
            repository.delete_verification_record(lexeme_id=lexeme.id, meaning_id=meaning_id)
            return
        prune_verification_record_action(
            repository,
            lexeme_id=lexeme.id,
            meaning_id=meaning_id,
            action=action,
        )


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
