from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Literal

from app.api.schemas.v1.wordbank import GeneratePronunciationResponse, QueuedBackgroundTask
from app.db.migrations import get_connection
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

    def __init__(self, tts_service: TTSService | None, db_path: Path) -> None:
        self._tts_service = tts_service
        self._db_path = db_path

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

        has_audio = bool(
            row is not None
            and isinstance(row["pronunciation_audio"], bytes)
            and row["pronunciation_audio"]
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
        conn: sqlite3.Connection,
        lexeme_id: int,
        form: str,
        force: bool = False,
    ) -> bool:
        existing_rows = conn.execute(
            """
            SELECT id, pronunciation_audio
            FROM surface_forms
            WHERE lexeme_id = ? AND form = ?
            ORDER BY id ASC
            """,
            (lexeme_id, form),
        ).fetchall()

        if (
            not force
            and existing_rows
            and all(isinstance(row["pronunciation_audio"], bytes) and row["pronunciation_audio"] for row in existing_rows)
        ):
            return False

        generated = self._lookup_pronunciation(form)
        if generated is None:
            return False
        generated = _normalize_pronunciation_audio(generated)

        if not existing_rows:
            conn.execute(
                """
                INSERT INTO surface_forms (
                    lexeme_id,
                    meaning_id,
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
                    None,
                    form,
                    "manual",
                    generated.audio_bytes,
                    generated.mime_type,
                    self._tts_provider_name(),
                    self._tts_model_name(),
                ),
            )
            return True

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
                    int(existing["id"]),
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
