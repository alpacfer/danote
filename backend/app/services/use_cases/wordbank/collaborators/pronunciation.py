from __future__ import annotations

from pathlib import Path
from typing import Literal

from app.api.schemas.v1.wordbank import GeneratePronunciationResponse, QueuedBackgroundTask
from app.db.migrations import get_connection
from app.db.repositories import WordbankRepository
from app.services.token_classifier import normalize_token
from app.services.tts import PronunciationAudio, TTSService
from app.services.use_cases.wordbank.shared import (
    _is_pcm_like_mime,
    _looks_like_wav,
    _normalize_pronunciation_audio,
    _pcm_to_wav_bytes,
)


class PronunciationCollaborator:
    """Handles TTS synthesis and pronunciation audio storage."""

    def __init__(self, tts_service: TTSService | None, db_path: Path, *, owner_user_id: int = 1) -> None:
        self._tts_service = tts_service
        self._db_path = db_path
        self._owner_user_id = owner_user_id

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

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

        generated_any = bool(
            self.generate_pronunciations_for_forms(
                normalized_lemma,
                requested_forms=forms_to_generate,
                force=force,
            )
        )
        repository = WordbankRepository(self._db_path, owner_user_id=self._owner_user_id)
        lexeme = repository.get_lexeme(normalized_lemma)
        if lexeme is None:
            raise LookupError(f"Lemma '{normalized_lemma}' was not found")
        has_audio = any(
            row.has_pronunciation
            for row in repository.find_surface_forms(lexeme_id=lexeme.id, form=pronunciation_form)
        )

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

    def generate_pronunciations_for_forms(
        self,
        stored_lemma: str,
        *,
        requested_forms: list[str],
        force: bool = False,
    ) -> list[str]:
        normalized_lemma = normalize_token(stored_lemma)
        if not normalized_lemma:
            raise ValueError("stored_lemma is required")
        if self._tts_service is None:
            return []

        repository = WordbankRepository(self._db_path, owner_user_id=self._owner_user_id)
        lexeme = repository.get_lexeme(normalized_lemma)
        if lexeme is None:
            raise LookupError(f"Lemma '{normalized_lemma}' was not found")

        generated_forms: list[str] = []
        seen: set[str] = set()
        forms_to_generate = [normalized_lemma, *requested_forms]
        for form in forms_to_generate:
            normalized_form = normalize_token(form)
            if not normalized_form or normalized_form in seen:
                continue
            seen.add(normalized_form)
            generated_now = self._ensure_surface_pronunciation(
                lexeme_id=lexeme.id,
                stored_lemma=normalized_lemma,
                form=normalized_form,
                force=force,
            )
            if generated_now:
                generated_forms.append(normalized_form)
        return generated_forms

    def queued_pronunciation_result(
        self,
        stored_lemma: str,
        stored_surface_form: str | None,
    ) -> QueuedBackgroundTask:
        normalized_lemma = normalize_token(stored_lemma)
        normalized_surface = normalize_token(stored_surface_form or "") or None
        pronunciation_form = normalized_surface or normalized_lemma or None
        if self._tts_service is None:
            return QueuedBackgroundTask(
                status="skipped",
                form=pronunciation_form,
            )
        return QueuedBackgroundTask(
            status="queued",
            form=pronunciation_form,
        )

    def get_pronunciation_audio(self, form: str) -> PronunciationAudio:
        normalized_form = normalize_token(form)
        if not normalized_form:
            raise ValueError("form is required")

        with get_connection(self._db_path) as conn:
            row = conn.execute(
                """
                SELECT id, pronunciation_audio, pronunciation_mime_type
                FROM surface_forms
                WHERE form = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (normalized_form,),
            ).fetchone()
            if row is None:
                raise LookupError(f"Pronunciation for '{normalized_form}' was not found")

            audio_bytes = row["pronunciation_audio"]
            if isinstance(audio_bytes, bytes) and audio_bytes:
                mime_type = row["pronunciation_mime_type"]
                normalized_mime = (
                    mime_type.strip().lower()
                    if isinstance(mime_type, str) and mime_type.strip()
                    else ""
                )
                if _is_pcm_like_mime(normalized_mime):
                    wav_bytes = _pcm_to_wav_bytes(audio_bytes)
                    conn.execute(
                        """
                        UPDATE surface_forms
                        SET pronunciation_audio = ?, pronunciation_mime_type = ?
                        WHERE id = ?
                        """,
                        (wav_bytes, "audio/wav", int(row["id"])),
                    )
                    return PronunciationAudio(audio_bytes=wav_bytes, mime_type="audio/wav")
                if _looks_like_wav(audio_bytes):
                    if normalized_mime not in {"audio/wav", "audio/x-wav"}:
                        conn.execute(
                            """
                            UPDATE surface_forms
                            SET pronunciation_mime_type = ?
                            WHERE id = ?
                            """,
                            ("audio/wav", int(row["id"])),
                        )
                    return PronunciationAudio(audio_bytes=audio_bytes, mime_type="audio/wav")
                return PronunciationAudio(
                    audio_bytes=audio_bytes,
                    mime_type=(
                        mime_type
                        if isinstance(mime_type, str) and mime_type.strip()
                        else "audio/wav"
                    ),
                )

            generated = self._lookup_pronunciation(normalized_form)
            if generated is None:
                if self._tts_service is None:
                    raise RuntimeError(
                        "Text-to-speech is unavailable: configure DANOTE_TTS_AZURE_API_KEY and DANOTE_TTS_AZURE_REGION."
                    )
                raise LookupError(f"Pronunciation for '{normalized_form}' was not found")
            generated = _normalize_pronunciation_audio(generated)

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
                    int(row["id"]),
                ),
            )
            return generated

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _ensure_surface_pronunciation(
        self,
        *,
        lexeme_id: int,
        stored_lemma: str,
        form: str,
        force: bool = False,
    ) -> bool:
        repository = WordbankRepository(self._db_path, owner_user_id=self._owner_user_id)
        existing_rows = repository.find_surface_forms(lexeme_id=lexeme_id, form=form)
        if not existing_rows and form == stored_lemma:
            repository.insert_or_update_surface_form(
                lexeme_id=lexeme_id,
                meaning_id=None,
                form=stored_lemma,
                pos_tag=None,
                morphology=None,
            )
            existing_rows = repository.find_surface_forms(lexeme_id=lexeme_id, form=form)

        if (
            not force
            and existing_rows
            and all(row.has_pronunciation for row in existing_rows)
        ):
            return False

        if not force:
            copied_existing_audio = self._copy_existing_surface_pronunciation(existing_rows)
            if copied_existing_audio:
                return True

        generated = self._lookup_pronunciation(form)
        if generated is None:
            return False
        generated = _normalize_pronunciation_audio(generated)

        if not existing_rows:
            return False

        with get_connection(self._db_path) as conn:
            for existing in existing_rows:
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
                        existing.id,
                    ),
                )
        return True

    def _copy_existing_surface_pronunciation(self, existing_rows) -> bool:
        source_row_id: int | None = None
        missing_row_ids: list[int] = []
        for row in existing_rows:
            if row.has_pronunciation and source_row_id is None:
                source_row_id = row.id
                continue
            if not row.has_pronunciation:
                missing_row_ids.append(row.id)

        if source_row_id is None or not missing_row_ids:
            return False

        with get_connection(self._db_path) as conn:
            audio_row = conn.execute(
                """
                SELECT
                    pronunciation_audio,
                    pronunciation_mime_type,
                    pronunciation_provider,
                    pronunciation_model,
                    pronunciation_generated_at
                FROM surface_forms
                WHERE id = ?
                LIMIT 1
                """,
                (source_row_id,),
            ).fetchone()
            if (
                audio_row is None
                or not isinstance(audio_row["pronunciation_audio"], bytes)
                or not audio_row["pronunciation_audio"]
            ):
                return False

            for row_id in missing_row_ids:
                conn.execute(
                    """
                    UPDATE surface_forms
                    SET pronunciation_audio = ?,
                        pronunciation_mime_type = ?,
                        pronunciation_provider = ?,
                        pronunciation_model = ?,
                        pronunciation_generated_at = COALESCE(?, CURRENT_TIMESTAMP)
                    WHERE id = ?
                    """,
                    (
                        audio_row["pronunciation_audio"],
                        audio_row["pronunciation_mime_type"],
                        audio_row["pronunciation_provider"],
                        audio_row["pronunciation_model"],
                        audio_row["pronunciation_generated_at"],
                        row_id,
                    ),
                )
        return True

    def _lookup_pronunciation(self, source_word: str) -> PronunciationAudio | None:
        if self._tts_service is None:
            return None
        synthesize = getattr(self._tts_service, "synthesize", None)
        if not callable(synthesize):
            return None
        try:
            return synthesize(source_word)
        except Exception:
            return None

    def _tts_provider_name(self) -> str:
        provider = getattr(self._tts_service, "provider", None)
        if isinstance(provider, str):
            cleaned = provider.strip().lower()
            if cleaned:
                return cleaned
        return "tts"

    def _tts_model_name(self) -> str | None:
        model = getattr(self._tts_service, "model", None)
        if isinstance(model, str):
            cleaned = model.strip()
            if cleaned:
                return cleaned
        return None
