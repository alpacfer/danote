from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from app.api.schemas.v1.wordbank import (
    AddWordResponse,
    ApplyVerificationChangesResponse,
    VerifyWordResponse,
)
from app.db.migrations import get_connection
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.collaborators.nlp import NLPCollaborator
from app.services.verification import WordVerificationInput, WordVerificationService

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

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

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
        suggested_changes: dict[str, str | None],
        provider: str | None = None,
    ) -> ApplyVerificationChangesResponse:
        normalized_lemma = normalize_token(stored_lemma)
        normalized_surface = normalize_token(stored_surface_form or "") or None
        if not normalized_lemma:
            raise ValueError("stored_lemma is required")

        accepted_fields = (
            "lemma_pos_tag",
            "lemma_morphology",
            "surface_pos_tag",
            "surface_morphology",
            "lexeme_translation",
        )
        normalized_changes: dict[str, str] = {}
        for field in accepted_fields:
            value = suggested_changes.get(field)
            if not isinstance(value, str):
                continue
            cleaned = value.strip()
            if cleaned:
                if field == "lexeme_translation":
                    from app.services.use_cases.wordbank.collaborators.translation import (
                        TranslationCollaborator,
                    )

                    cleaned = TranslationCollaborator.normalize_translation_value(cleaned) or ""
                    if not cleaned:
                        continue
                normalized_changes[field] = cleaned

        if not normalized_changes:
            return ApplyVerificationChangesResponse(
                status="skipped",
                stored_lemma=normalized_lemma,
                stored_surface_form=normalized_surface,
                applied_fields=[],
            )

        needs_surface = any(
            field in normalized_changes
            for field in ("surface_pos_tag", "surface_morphology")
        )
        if needs_surface and not normalized_surface:
            raise ValueError(
                "stored_surface_form is required for surface-level verification changes."
            )

        provider_name = (
            provider.strip().lower()
            if isinstance(provider, str) and provider.strip()
            else "verification"
        )
        applied_fields: list[str] = []
        lexeme_before: dict[str, str | None] | None = None
        surface_before: dict[str, str | None] | None = None

        with get_connection(self._db_path) as conn:
            lexeme_row = conn.execute(
                """
                SELECT id, pos_tag, morphology, english_translation, translation_provider
                FROM lexemes
                WHERE lemma = ?
                LIMIT 1
                """,
                (normalized_lemma,),
            ).fetchone()
            if lexeme_row is None:
                raise LookupError(f"Lemma '{normalized_lemma}' was not found")
            lexeme_id = int(lexeme_row["id"])
            meaning_row = self._load_meaning_row(
                conn,
                lexeme_id=lexeme_id,
                requested_meaning_id=meaning_id,
                normalized_lemma=normalized_lemma,
            )

            if meaning_row is not None:
                lexeme_before = {
                    "pos_tag": meaning_row["pos_tag"],
                    "morphology": meaning_row["morphology"],
                    "english_translation": meaning_row["english_translation"],
                    "translation_provider": "meaning_section",
                }
            else:
                lexeme_before = {
                    "pos_tag": lexeme_row["pos_tag"],
                    "morphology": lexeme_row["morphology"],
                    "english_translation": lexeme_row["english_translation"],
                    "translation_provider": lexeme_row["translation_provider"],
                }

            lexeme_updates: list[str] = []
            lexeme_params: list[str | int] = []
            if "lemma_pos_tag" in normalized_changes:
                lexeme_updates.append("pos_tag = ?")
                lexeme_params.append(normalized_changes["lemma_pos_tag"])
                applied_fields.append("lemma_pos_tag")
            if "lemma_morphology" in normalized_changes:
                lexeme_updates.append("morphology = ?")
                lexeme_params.append(normalized_changes["lemma_morphology"])
                applied_fields.append("lemma_morphology")
            if "lexeme_translation" in normalized_changes:
                lexeme_updates.append("english_translation = ?")
                lexeme_params.append(normalized_changes["lexeme_translation"])
                if meaning_row is None:
                    lexeme_updates.append("translation_provider = ?")
                    lexeme_params.append(provider_name)
                applied_fields.append("lexeme_translation")

            if lexeme_updates:
                if meaning_row is not None:
                    conn.execute(
                        f"UPDATE lexeme_meanings SET {', '.join(lexeme_updates)} WHERE id = ?",
                        (*lexeme_params, int(meaning_row["id"])),
                    )
                else:
                    conn.execute(
                        f"UPDATE lexemes SET {', '.join(lexeme_updates)} WHERE id = ?",
                        (*lexeme_params, lexeme_id),
                    )

            if normalized_surface:
                if meaning_row is not None:
                    surface_row = conn.execute(
                        """
                        SELECT pos_tag, morphology
                        FROM surface_forms
                        WHERE meaning_id = ? AND form = ?
                        LIMIT 1
                        """,
                        (int(meaning_row["id"]), normalized_surface),
                    ).fetchone()
                else:
                    surface_row = conn.execute(
                        """
                        SELECT pos_tag, morphology
                        FROM surface_forms
                        WHERE lexeme_id = ? AND meaning_id IS NULL AND form = ?
                        LIMIT 1
                        """,
                        (lexeme_id, normalized_surface),
                    ).fetchone()
                if surface_row is not None:
                    surface_before = {
                        "pos_tag": surface_row["pos_tag"],
                        "morphology": surface_row["morphology"],
                    }
                conn.execute(
                    """
                    INSERT OR IGNORE INTO surface_forms (lexeme_id, meaning_id, form, source)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        lexeme_id,
                        int(meaning_row["id"]) if meaning_row is not None else None,
                        normalized_surface,
                        "manual",
                    ),
                )

                surface_updates: list[str] = []
                surface_params: list[str | int] = []
                if "surface_pos_tag" in normalized_changes:
                    surface_updates.append("pos_tag = ?")
                    surface_params.append(normalized_changes["surface_pos_tag"])
                    applied_fields.append("surface_pos_tag")
                if "surface_morphology" in normalized_changes:
                    surface_updates.append("morphology = ?")
                    surface_params.append(normalized_changes["surface_morphology"])
                    applied_fields.append("surface_morphology")

                if surface_updates:
                    if meaning_row is not None:
                        conn.execute(
                            f"""
                            UPDATE surface_forms
                            SET {", ".join(surface_updates)}
                            WHERE meaning_id = ? AND form = ?
                            """,
                            (*surface_params, int(meaning_row["id"]), normalized_surface),
                        )
                    else:
                        conn.execute(
                            f"""
                            UPDATE surface_forms
                            SET {", ".join(surface_updates)}
                            WHERE lexeme_id = ? AND meaning_id IS NULL AND form = ?
                            """,
                            (*surface_params, lexeme_id, normalized_surface),
                        )

        self._nlp.invalidate_pos_cache(normalized_lemma, normalized_surface)
        if applied_fields and provider_name == "gemini":
            self._append_gemini_change_log(
                {
                    "timestamp_utc": datetime.now(UTC).isoformat(),
                    "provider": provider_name,
                    "stored_lemma": normalized_lemma,
                    "stored_surface_form": normalized_surface,
                    "applied_fields": applied_fields,
                    "suggested_changes": {
                        key: normalized_changes[key]
                        for key in accepted_fields
                        if key in normalized_changes
                    },
                    "before": {
                        "lexeme": lexeme_before,
                        "surface": surface_before,
                    },
                }
            )

        return ApplyVerificationChangesResponse(
            status="applied" if applied_fields else "skipped",
            stored_lemma=normalized_lemma,
            stored_surface_form=normalized_surface,
            applied_fields=applied_fields,
        )

    def queued_verification_result(self) -> AddWordResponse.VerificationResult:
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

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

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

    def _verification_metadata(self) -> tuple[str, str | None]:
        provider = getattr(self._verification_service, "provider", None)
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
                meaning_row = self._load_meaning_row(
                    conn,
                    lexeme_id=int(lexeme_row["id"]),
                    requested_meaning_id=meaning_id,
                    normalized_lemma=stored_lemma,
                )
                if meaning_row is not None:
                    lexeme_translation = meaning_row["english_translation"]
                    lexeme_translation_provider = "meaning_section"
                else:
                    lexeme_translation = lexeme_row["english_translation"]
                    lexeme_translation_provider = lexeme_row["translation_provider"]

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
            surface_pos_tag, surface_morphology = self._nlp.extract_pos_and_morphology(
                stored_surface_form
            )

        return WordVerificationInput(
            stored_lemma=stored_lemma,
            stored_surface_form=stored_surface_form,
            lexeme_source=lexeme_source,
            lexeme_translation=lexeme_translation,
            lexeme_translation_provider=lexeme_translation_provider,
            surface_source=surface_source,
            lemma_pos_tag=lemma_pos_tag,
            lemma_morphology=lemma_morphology,
            surface_pos_tag=surface_pos_tag,
            surface_morphology=surface_morphology,
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
                SELECT id, pos_tag, morphology, english_translation
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
            SELECT id, pos_tag, morphology, english_translation
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
        self, payload: WordVerificationInput
    ) -> AddWordResponse.VerificationResult:
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
