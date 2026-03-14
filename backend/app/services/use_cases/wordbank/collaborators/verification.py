from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Literal

from app.api.schemas.v1.wordbank import (
    ApplyVerificationChangesResponse,
    VerificationAction,
    VerificationResult,
    VerifyWordResponse,
)
from app.db.migrations import get_connection
from app.db.repositories.wordbank import WordbankRepository
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.collaborators.cor import CorResolutionCollaborator
from app.services.use_cases.wordbank.collaborators.nlp import NLPCollaborator
from app.services.use_cases.wordbank.verification_actions import apply_verification_action
from app.services.use_cases.wordbank.verification_apply_resolution import (
    update_persisted_verification_after_apply,
)
from app.services.use_cases.wordbank.verification_records import (
    now_utc_iso,
    persist_verification_result,
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
        verification = self._verify_added_word(payload)
        self._persist_verification_result(
            stored_lemma=normalized_lemma,
            meaning_id=meaning_id,
            stored_surface_form=normalized_surface,
            verification=verification,
        )
        return VerifyWordResponse(
            stored_lemma=normalized_lemma,
            stored_surface_form=normalized_surface,
            verification=verification,
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
        verification = self._verify_added_word(payload)
        self._persist_verification_result(
            stored_lemma=normalized_lemma,
            meaning_id=meaning_id,
            stored_surface_form=normalized_surface,
            verification=verification,
        )
        return True

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
    ) -> WordVerificationInput:
        lexeme_source = "manual"
        selected_translation: str | None = None
        selected_translation_scope: Literal["lemma", "meaning_section"] | None = None
        surface_source: str | None = None
        meaning_key: str | None = None
        meaning_gloss: str | None = None
        sibling_meaning_sections: list[WordVerificationMeaningSection] = []
        lexeme_pos_tag: str | None = None
        lexeme_morphology: str | None = None
        selected_meaning_pos_tag: str | None = None
        selected_meaning_morphology: str | None = None
        selected_surface_pos_tag: str | None = None
        selected_surface_morphology: str | None = None
        selected_surface_row = None
        surface_cor_entry = None
        canonical_lemma_entry = None

        with get_connection(self._db_path) as conn:
            lexeme_row = conn.execute(
                """
                SELECT id, source, english_translation, pos_tag, morphology
                FROM lexemes
                WHERE lemma = ?
                LIMIT 1
                """,
                (stored_lemma,),
            ).fetchone()

            if lexeme_row is not None:
                lexeme_source = lexeme_row["source"]
                lexeme_pos_tag = lexeme_row["pos_tag"]
                lexeme_morphology = lexeme_row["morphology"]
                meaning_rows = conn.execute(
                    """
                    SELECT id, meaning_key, cor_lemma_idx, gloss, english_translation, pos_tag, morphology
                    FROM lexeme_meanings
                    WHERE lexeme_id = ?
                    ORDER BY id ASC
                    """,
                    (int(lexeme_row["id"]),),
                ).fetchall()
                surface_rows = conn.execute(
                    """
                    SELECT
                        sf.form,
                        sf.meaning_id,
                        sf.source,
                        sf.pos_tag,
                        sf.morphology,
                        (
                            SELECT sfcv.cor_id
                            FROM surface_form_cor_variants sfcv
                            WHERE sfcv.surface_form_id = sf.id
                            ORDER BY sfcv.id ASC
                            LIMIT 1
                        ) AS cor_id
                    FROM surface_forms sf
                    WHERE sf.lexeme_id = ?
                    ORDER BY sf.id ASC
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
                    selected_translation = meaning_row["english_translation"]
                    selected_translation_scope = "meaning_section" if selected_translation else None
                    meaning_key = meaning_row["meaning_key"]
                    meaning_gloss = meaning_row["gloss"]
                    selected_meaning_pos_tag = meaning_row["pos_tag"]
                    selected_meaning_morphology = meaning_row["morphology"]
                else:
                    selected_translation = lexeme_row["english_translation"]
                    selected_translation_scope = "lemma" if selected_translation else None

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
                    selected_surface_row = self._select_surface_row(
                        surface_rows,
                        stored_surface_form=stored_surface_form,
                        meaning_id=meaning_id,
                    )
                    if selected_surface_row is not None:
                        surface_source = selected_surface_row["source"]
                        selected_surface_pos_tag = selected_surface_row["pos_tag"]
                        selected_surface_morphology = selected_surface_row["morphology"]
                        surface_cor_entry = self._cor.cor_local_entry_for_cor_id(
                            cor_id=selected_surface_row["cor_id"]
                        ) if selected_surface_row["cor_id"] else None

                canonical_lemma_entry = self._resolve_canonical_lemma_entry(
                    stored_lemma=stored_lemma,
                    meaning_row=meaning_row,
                    selected_surface_row=selected_surface_row,
                    fallback_pos_tag=selected_meaning_pos_tag or lexeme_pos_tag,
                )
                if stored_surface_form and surface_cor_entry is None:
                    surface_cor_entry = self._cor.best_cor_local_entry_for_form(
                        form=stored_surface_form,
                        lemma=stored_lemma,
                        preferred_pos_tag=selected_surface_pos_tag or selected_meaning_pos_tag or lexeme_pos_tag,
                    )

        canonical_lemma_pos_tag, canonical_lemma_morphology = self._resolve_canonical_lemma_metadata(
            stored_lemma=stored_lemma,
            lexeme_pos_tag=lexeme_pos_tag,
            lexeme_morphology=lexeme_morphology,
            selected_meaning_pos_tag=selected_meaning_pos_tag,
            selected_meaning_morphology=selected_meaning_morphology,
            canonical_lemma_entry=canonical_lemma_entry,
        )
        if selected_meaning_pos_tag is None:
            selected_meaning_pos_tag = canonical_lemma_entry.pos_tag if canonical_lemma_entry is not None else None
        if selected_meaning_morphology is None:
            selected_meaning_morphology = (
                canonical_lemma_entry.morphology if canonical_lemma_entry is not None else None
            )
        if stored_surface_form and selected_surface_pos_tag is None:
            selected_surface_pos_tag = surface_cor_entry.pos_tag if surface_cor_entry is not None else None
        if stored_surface_form and selected_surface_morphology is None:
            selected_surface_morphology = surface_cor_entry.morphology if surface_cor_entry is not None else None
        if canonical_lemma_pos_tag is None or canonical_lemma_morphology is None:
            inferred_lemma_pos_tag, inferred_lemma_morphology = self._nlp.extract_pos_and_morphology(stored_lemma)
            canonical_lemma_pos_tag = canonical_lemma_pos_tag or inferred_lemma_pos_tag
            canonical_lemma_morphology = canonical_lemma_morphology or inferred_lemma_morphology
        if stored_surface_form and (selected_surface_pos_tag is None or selected_surface_morphology is None):
            inferred_surface_pos_tag, inferred_surface_morphology = self._nlp.extract_pos_and_morphology(
                stored_surface_form
            )
            selected_surface_pos_tag = selected_surface_pos_tag or inferred_surface_pos_tag
            selected_surface_morphology = selected_surface_morphology or inferred_surface_morphology

        return WordVerificationInput(
            stored_lemma=stored_lemma,
            stored_surface_form=stored_surface_form,
            meaning_id=meaning_id,
            meaning_key=meaning_key,
            meaning_gloss=meaning_gloss,
            lexeme_source=lexeme_source,
            selected_translation=selected_translation,
            selected_translation_scope=selected_translation_scope,
            surface_source=surface_source,
            canonical_lemma_pos_tag=canonical_lemma_pos_tag,
            canonical_lemma_morphology=canonical_lemma_morphology,
            selected_meaning_pos_tag=selected_meaning_pos_tag,
            selected_meaning_morphology=selected_meaning_morphology,
            selected_surface_pos_tag=selected_surface_pos_tag,
            selected_surface_morphology=selected_surface_morphology,
            sibling_meaning_sections=tuple(sibling_meaning_sections),
        )

    def _select_surface_row(self, surface_rows, *, stored_surface_form: str, meaning_id: int | None):
        for row in surface_rows:
            if str(row["form"]) != stored_surface_form:
                continue
            row_meaning_id = int(row["meaning_id"]) if row["meaning_id"] is not None else None
            if row_meaning_id == meaning_id:
                return row
        return None

    def _resolve_canonical_lemma_entry(
        self,
        *,
        stored_lemma: str,
        meaning_row,
        selected_surface_row,
        fallback_pos_tag: str | None,
    ):
        cor_lemma_idx = int(meaning_row["cor_lemma_idx"]) if meaning_row is not None and meaning_row["cor_lemma_idx"] is not None else None
        if cor_lemma_idx is not None:
            entry = self._cor.best_cor_local_lemma_entry(
                lemma_idx=cor_lemma_idx,
                lemma=stored_lemma,
                preferred_pos_tag=fallback_pos_tag,
            )
            if entry is not None:
                return entry
        if selected_surface_row is None or not selected_surface_row["cor_id"]:
            return None
        surface_entry = self._cor.cor_local_entry_for_cor_id(cor_id=str(selected_surface_row["cor_id"]))
        if surface_entry is None:
            return None
        return self._cor.best_cor_local_lemma_entry(
            lemma_idx=surface_entry.lemma_idx,
            lemma=stored_lemma,
            preferred_pos_tag=fallback_pos_tag or surface_entry.pos_tag,
        )

    def _resolve_canonical_lemma_metadata(
        self,
        *,
        stored_lemma: str,
        lexeme_pos_tag: str | None,
        lexeme_morphology: str | None,
        selected_meaning_pos_tag: str | None,
        selected_meaning_morphology: str | None,
        canonical_lemma_entry,
    ) -> tuple[str | None, str | None]:
        canonical_pos_tag = (
            canonical_lemma_entry.pos_tag if canonical_lemma_entry is not None else None
        ) or lexeme_pos_tag or selected_meaning_pos_tag
        canonical_morphology = (
            canonical_lemma_entry.morphology if canonical_lemma_entry is not None else None
        ) or lexeme_morphology or selected_meaning_morphology
        if canonical_pos_tag is not None and canonical_morphology is not None:
            return canonical_pos_tag, canonical_morphology
        inferred_pos_tag, inferred_morphology = self._nlp.extract_pos_and_morphology(stored_lemma)
        return canonical_pos_tag or inferred_pos_tag, canonical_morphology or inferred_morphology

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
                SELECT id, meaning_key, cor_lemma_idx, gloss, english_translation, pos_tag, morphology
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
            SELECT id, meaning_key, cor_lemma_idx, gloss, english_translation, pos_tag, morphology
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
        stored_surface_form: str | None,
        verification: VerificationResult,
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
