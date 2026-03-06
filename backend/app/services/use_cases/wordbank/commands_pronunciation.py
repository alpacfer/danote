from __future__ import annotations

from app.api.schemas.v1.wordbank import GeneratePronunciationResponse
from app.db.migrations import get_connection
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.shared import _normalize_pronunciation_audio


class WordbankCommandsPronunciationMixin:
    def generate_pronunciation_for_added_word(
        self,
        stored_lemma: str,
        stored_surface_form: str | None,
        *,
        force: bool = False,
    ) -> GeneratePronunciationResponse:
        normalized_lemma = normalize_token(stored_lemma)
        normalized_surface = normalize_token(stored_surface_form or "") or None
        if not normalized_lemma:
            raise ValueError("stored_lemma is required")

        pronunciation_form = normalized_surface or normalized_lemma
        forms_to_generate = [normalized_lemma]
        if normalized_surface and normalized_surface != normalized_lemma:
            forms_to_generate.append(normalized_surface)
        if not pronunciation_form:
            return GeneratePronunciationResponse(
                status="skipped",
                stored_lemma=normalized_lemma,
                stored_surface_form=normalized_surface,
                pronunciation_form=None,
            )

        if self._tts_service is None:
            return GeneratePronunciationResponse(
                status="unavailable",
                stored_lemma=normalized_lemma,
                stored_surface_form=normalized_surface,
                pronunciation_form=pronunciation_form,
            )

        with get_connection(self._db_path) as conn:
            lexeme_row = conn.execute(
                "SELECT id FROM lexemes WHERE lemma = ? LIMIT 1",
                (normalized_lemma,),
            ).fetchone()
            if lexeme_row is None:
                raise LookupError(f"Lemma '{normalized_lemma}' was not found")
            generated_any = False
            for form in forms_to_generate:
                generated_now = self._ensure_surface_pronunciation(
                    conn=conn,
                    lexeme_id=int(lexeme_row["id"]),
                    form=form,
                    force=force,
                )
                generated_any = generated_any or generated_now
            row = conn.execute(
                """
                SELECT pronunciation_audio
                FROM surface_forms
                WHERE lexeme_id = ? AND form = ?
                LIMIT 1
                """,
                (int(lexeme_row["id"]), pronunciation_form),
            ).fetchone()

        has_audio = bool(row is not None and isinstance(row["pronunciation_audio"], bytes) and row["pronunciation_audio"])
        if force and not generated_any:
            status: Literal["generated", "unavailable", "skipped"] = "unavailable"
        else:
            status = "generated" if has_audio else "unavailable"
        return GeneratePronunciationResponse(
            status=status,
            stored_lemma=normalized_lemma,
            stored_surface_form=normalized_surface,
            pronunciation_form=pronunciation_form,
        )



    def _ensure_surface_pronunciation(
        self,
        *,
        conn: sqlite3.Connection,
        lexeme_id: int,
        form: str,
        force: bool = False,
    ) -> bool:
        existing = conn.execute(
            """
            SELECT id, pronunciation_audio
            FROM surface_forms
            WHERE lexeme_id = ? AND form = ?
            LIMIT 1
            """,
            (lexeme_id, form),
        ).fetchone()

        existing_audio = existing["pronunciation_audio"] if existing is not None else None
        if not force and isinstance(existing_audio, bytes) and existing_audio:
            return False

        generated = self._lookup_pronunciation(form)
        if generated is None:
            return False
        generated = _normalize_pronunciation_audio(generated)

        if existing is None:
            conn.execute(
                """
                INSERT INTO surface_forms (
                    lexeme_id,
                    form,
                    source,
                    pronunciation_audio,
                    pronunciation_mime_type,
                    pronunciation_provider,
                    pronunciation_model,
                    pronunciation_generated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    lexeme_id,
                    form,
                    "manual",
                    generated.audio_bytes,
                    generated.mime_type,
                    self._tts_provider_name(),
                    self._tts_model_name(),
                ),
            )
            return True

        conn.execute(
            """
            UPDATE surface_forms
            SET pronunciation_audio = ?,
                pronunciation_mime_type = ?,
                pronunciation_provider = ?,
                pronunciation_model = ?,
                pronunciation_generated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                generated.audio_bytes,
                generated.mime_type,
                self._tts_provider_name(),
                self._tts_model_name(),
                int(existing["id"]),
            ),
        )
        return True


