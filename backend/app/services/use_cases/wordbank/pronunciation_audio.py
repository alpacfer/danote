from __future__ import annotations

from app.db.migrations import get_connection
from app.services.tts import PronunciationAudio
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.shared import _is_pcm_like_mime, _looks_like_wav, _normalize_pronunciation_audio, _pcm_to_wav_bytes


class WordbankPronunciationAudioMixin:
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
                normalized_mime = mime_type.strip().lower() if isinstance(mime_type, str) and mime_type.strip() else ""
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
                    mime_type=mime_type if isinstance(mime_type, str) and mime_type.strip() else "audio/wav",
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


