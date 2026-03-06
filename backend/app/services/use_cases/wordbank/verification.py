from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from app.api.schemas.v1.wordbank import AddWordResponse
from app.db.migrations import get_connection
from app.services.verification import WordVerificationInput

logger = logging.getLogger(__name__)

class WordbankVerificationMixin:
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


    def _queued_verification_result(self) -> AddWordResponse.VerificationResult:
        if self._verification_service is None:
            return AddWordResponse.VerificationResult(
                status="skipped",
                provider=None,
                reviewer_role=None,
                message="Word verification is disabled.",
            )

        provider_name, reviewer_name = self._verification_metadata()
        return AddWordResponse.VerificationResult(
            status="queued",
            provider=provider_name,
            reviewer_role=reviewer_name,
            message="Word verification queued.",
            composed_word_count=None,
        )


    def _verification_metadata(self) -> tuple[str, str | None]:
        provider = getattr(self._verification_service, "provider", None)
        reviewer_role = getattr(self._verification_service, "reviewer_role", None)
        provider_name = provider.strip().lower() if isinstance(provider, str) and provider.strip() else "verification"
        reviewer_name = reviewer_role.strip() if isinstance(reviewer_role, str) and reviewer_role.strip() else None
        return provider_name, reviewer_name


    def _build_verification_input(
        self,
        *,
        stored_lemma: str,
        stored_surface_form: str | None,
    ) -> WordVerificationInput:
        lexeme_source = "manual"
        lexeme_translation: str | None = None
        lexeme_translation_provider: str | None = None
        surface_source: str | None = None
        surface_translation: str | None = None
        surface_translation_provider: str | None = None

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
                lexeme_translation = lexeme_row["english_translation"]
                lexeme_translation_provider = lexeme_row["translation_provider"]

                if stored_surface_form:
                    surface_row = conn.execute(
                        """
                        SELECT source, english_translation, translation_provider
                        FROM surface_forms
                        WHERE lexeme_id = ? AND form = ?
                        LIMIT 1
                        """,
                        (lexeme_row["id"], stored_surface_form),
                    ).fetchone()
                    if surface_row is not None:
                        surface_source = surface_row["source"]
                        surface_translation = surface_row["english_translation"]
                        surface_translation_provider = surface_row["translation_provider"]

        lemma_pos_tag, lemma_morphology = self._extract_pos_and_morphology(stored_lemma)
        surface_pos_tag: str | None = None
        surface_morphology: str | None = None
        if stored_surface_form:
            surface_pos_tag, surface_morphology = self._extract_pos_and_morphology(stored_surface_form)

        return WordVerificationInput(
            stored_lemma=stored_lemma,
            stored_surface_form=stored_surface_form,
            lexeme_source=lexeme_source,
            lexeme_translation=lexeme_translation,
            lexeme_translation_provider=lexeme_translation_provider,
            surface_source=surface_source,
            surface_translation=surface_translation,
            surface_translation_provider=surface_translation_provider,
            lemma_pos_tag=lemma_pos_tag,
            lemma_morphology=lemma_morphology,
            surface_pos_tag=surface_pos_tag,
            surface_morphology=surface_morphology,
        )


    def _verify_added_word(self, payload: WordVerificationInput) -> AddWordResponse.VerificationResult:
        if self._verification_service is None:
            return AddWordResponse.VerificationResult(
                status="skipped",
                provider=None,
                reviewer_role=None,
                message="Word verification is disabled.",
            )

        provider_name, reviewer_name = self._verification_metadata()

        try:
            verdict = self._verification_service.verify_word_entry(payload)
        except Exception as exc:
            return AddWordResponse.VerificationResult(
                status="error",
                provider=provider_name,
                reviewer_role=reviewer_name,
                message=f"Verification task failed: {exc}",
                composed_word_count=None,
                problem=str(exc),
                change_to_implement=(
                    "Fix Gemini verification setup or provider errors, then run verification again."
                ),
                suggested_changes=None,
            )

        return AddWordResponse.VerificationResult(
            status=verdict.verdict,
            provider=provider_name,
            reviewer_role=reviewer_name,
            message=verdict.message,
            composed_word_count=getattr(verdict, "composed_word_count", None),
            problem=getattr(verdict, "problem", None),
            change_to_implement=getattr(verdict, "change_to_implement", None),
            suggested_changes=getattr(verdict, "suggested_changes", None),
        )
