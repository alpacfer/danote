from __future__ import annotations

from pathlib import Path

from app.api.schemas.v1.sentencebank import (
    GenerateSentencePronunciationResponse,
    QueuedSentencePronunciationTask,
)
from app.db.migrations import get_connection
from app.db.repositories import SentencebankRepository
from app.services.tts import PronunciationAudio, TTSService
from app.services.use_cases.wordbank.shared import (
    _is_pcm_like_mime,
    _looks_like_wav,
    _normalize_pronunciation_audio,
    _pcm_to_wav_bytes,
)


class SentencePronunciationCollaborator:
    def __init__(self, tts_service: TTSService | None, db_path: Path, *, owner_user_id: int = 1) -> None:
        self._tts_service = tts_service
        self._db_path = db_path
        self._owner_user_id = owner_user_id
        self._repository = SentencebankRepository(db_path, owner_user_id=owner_user_id)

    def queued_pronunciation_result(self, sentence_id: int) -> QueuedSentencePronunciationTask:
        return QueuedSentencePronunciationTask(
            status="queued" if self._tts_service is not None else "skipped",
            sentence_id=sentence_id,
        )

    def generate_pronunciation_for_sentence(
        self,
        sentence_id: int,
        *,
        force: bool = False,
    ) -> GenerateSentencePronunciationResponse:
        sentence = self._repository.get_sentence(sentence_id)
        if sentence is None:
            raise LookupError(f"Sentence '{sentence_id}' was not found")

        if self._tts_service is None:
            return GenerateSentencePronunciationResponse(
                status="unavailable",
                sentence_id=sentence.id,
                source_text=sentence.source_text,
            )

        generated_now = self._ensure_sentence_pronunciation(
            sentence_id=sentence.id,
            source_text=sentence.source_text,
            force=force,
        )
        refreshed = self._repository.get_sentence(sentence.id)
        if refreshed is None:
            raise RuntimeError("Sentence pronunciation was generated but the sentence could not be reloaded.")

        if force and not generated_now and not refreshed.has_pronunciation:
            status = "unavailable"
        else:
            status = "generated" if refreshed.has_pronunciation else "unavailable"

        return GenerateSentencePronunciationResponse(
            status=status,
            sentence_id=sentence.id,
            source_text=refreshed.source_text,
        )

    def get_pronunciation_audio(self, sentence_id: int) -> PronunciationAudio:
        sentence = self._repository.get_sentence(sentence_id)
        if sentence is None:
            raise LookupError(f"Sentence '{sentence_id}' was not found")

        with get_connection(self._db_path) as conn:
            row = conn.execute(
                """
                SELECT pronunciation_audio, pronunciation_mime_type
                FROM sentence_bank
                WHERE id = ? AND owner_user_id = ?
                LIMIT 1
                """,
                (sentence_id, self._owner_user_id),
            ).fetchone()
            if row is None:
                raise LookupError(f"Sentence '{sentence_id}' was not found")

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
                        UPDATE sentence_bank
                        SET pronunciation_audio = ?,
                            pronunciation_mime_type = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (wav_bytes, "audio/wav", sentence_id),
                    )
                    return PronunciationAudio(audio_bytes=wav_bytes, mime_type="audio/wav")
                if _looks_like_wav(audio_bytes):
                    if normalized_mime not in {"audio/wav", "audio/x-wav"}:
                        conn.execute(
                            """
                            UPDATE sentence_bank
                            SET pronunciation_mime_type = ?,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                            """,
                            ("audio/wav", sentence_id),
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

        generated_now = self._ensure_sentence_pronunciation(
            sentence_id=sentence.id,
            source_text=sentence.source_text,
            force=False,
        )
        if not generated_now:
            if self._tts_service is None:
                raise RuntimeError(
                    "Text-to-speech is unavailable: configure DANOTE_TTS_AZURE_API_KEY and DANOTE_TTS_AZURE_REGION."
                )
            raise LookupError(f"Pronunciation for sentence '{sentence_id}' was not found")

        with get_connection(self._db_path, read_only=True) as conn:
            row = conn.execute(
                """
                SELECT pronunciation_audio, pronunciation_mime_type
                FROM sentence_bank
                WHERE id = ? AND owner_user_id = ?
                LIMIT 1
                """,
                (sentence_id, self._owner_user_id),
            ).fetchone()
        if row is None or not isinstance(row["pronunciation_audio"], bytes):
            raise LookupError(f"Pronunciation for sentence '{sentence_id}' was not found")
        return PronunciationAudio(
            audio_bytes=row["pronunciation_audio"],
            mime_type=str(row["pronunciation_mime_type"] or "audio/wav"),
        )

    def _ensure_sentence_pronunciation(
        self,
        *,
        sentence_id: int,
        source_text: str,
        force: bool,
    ) -> bool:
        sentence = self._repository.get_sentence(sentence_id)
        if sentence is None:
            raise LookupError(f"Sentence '{sentence_id}' was not found")
        if self._tts_service is None:
            return False
        if sentence.has_pronunciation and not force:
            return False

        generated = self._tts_service.synthesize(source_text)
        if generated is None:
            return False
        generated = _normalize_pronunciation_audio(generated)
        self._repository.update_pronunciation(
            sentence_id=sentence_id,
            audio_bytes=generated.audio_bytes,
            mime_type=generated.mime_type,
            provider=self._tts_provider_name(),
            model=self._tts_model_name(),
        )
        return True

    def _tts_provider_name(self) -> str | None:
        provider = getattr(self._tts_service, "provider", None)
        if isinstance(provider, str) and provider.strip():
            return provider.strip()
        return None

    def _tts_model_name(self) -> str | None:
        model = getattr(self._tts_service, "model", None)
        if isinstance(model, str) and model.strip():
            return model.strip()
        return None
