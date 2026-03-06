from __future__ import annotations

from datetime import UTC, datetime

from app.api.schemas.v1.wordbank import ApplyVerificationChangesResponse, VerifyWordResponse
from app.db.migrations import get_connection
from app.services.token_classifier import normalize_token


class WordbankCommandsVerificationApplyMixin:
    def verify_added_word(self, stored_lemma: str, stored_surface_form: str | None) -> VerifyWordResponse:
        normalized_lemma = normalize_token(stored_lemma)
        normalized_surface = normalize_token(stored_surface_form or "") or None
        if not normalized_lemma:
            raise ValueError("stored_lemma is required")

        payload = self._build_verification_input(
            stored_lemma=normalized_lemma,
            stored_surface_form=normalized_surface,
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
            "surface_translation",
        )
        normalized_changes: dict[str, str] = {}
        for field in accepted_fields:
            value = suggested_changes.get(field)
            if not isinstance(value, str):
                continue
            cleaned = value.strip()
            if cleaned:
                if field in {"lexeme_translation", "surface_translation"}:
                    cleaned = self._normalize_translation_value(cleaned) or ""
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
            for field in ("surface_pos_tag", "surface_morphology", "surface_translation")
        )
        if needs_surface and not normalized_surface:
            raise ValueError("stored_surface_form is required for surface-level verification changes.")

        provider_name = provider.strip().lower() if isinstance(provider, str) and provider.strip() else "verification"
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
                lexeme_updates.append("translation_provider = ?")
                lexeme_params.append(normalized_changes["lexeme_translation"])
                lexeme_params.append(provider_name)
                applied_fields.append("lexeme_translation")

            if lexeme_updates:
                conn.execute(
                    f"UPDATE lexemes SET {', '.join(lexeme_updates)} WHERE id = ?",
                    (*lexeme_params, lexeme_id),
                )

            if normalized_surface:
                surface_row = conn.execute(
                    """
                    SELECT pos_tag, morphology, english_translation, translation_provider
                    FROM surface_forms
                    WHERE lexeme_id = ? AND form = ?
                    LIMIT 1
                    """,
                    (lexeme_id, normalized_surface),
                ).fetchone()
                if surface_row is not None:
                    surface_before = {
                        "pos_tag": surface_row["pos_tag"],
                        "morphology": surface_row["morphology"],
                        "english_translation": surface_row["english_translation"],
                        "translation_provider": surface_row["translation_provider"],
                    }
                conn.execute(
                    """
                    INSERT OR IGNORE INTO surface_forms (lexeme_id, form, source)
                    VALUES (?, ?, ?)
                    """,
                    (lexeme_id, normalized_surface, "manual"),
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
                if "surface_translation" in normalized_changes:
                    surface_updates.append("english_translation = ?")
                    surface_updates.append("translation_provider = ?")
                    surface_params.append(normalized_changes["surface_translation"])
                    surface_params.append(provider_name)
                    applied_fields.append("surface_translation")

                if surface_updates:
                    conn.execute(
                        f"""
                        UPDATE surface_forms
                        SET {", ".join(surface_updates)}
                        WHERE lexeme_id = ? AND form = ?
                        """,
                        (*surface_params, lexeme_id, normalized_surface),
                    )

        self._invalidate_pos_cache(normalized_lemma, normalized_surface)
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


