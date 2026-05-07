from __future__ import annotations

from pathlib import Path

from app.db.migrations import get_connection
from app.services.tts import PronunciationAudio


class PresavedWordsAudioRepository:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def get(self, term: str) -> PronunciationAudio | None:
        with get_connection(self._db_path) as conn:
            row = conn.execute(
                "SELECT audio, mime_type FROM presaved_words_audio WHERE term = ? LIMIT 1",
                (term.strip().lower(),),
            ).fetchone()
        if row is None:
            return None
        audio_bytes = row["audio"]
        if not isinstance(audio_bytes, bytes) or not audio_bytes:
            return None
        return PronunciationAudio(
            audio_bytes=audio_bytes,
            mime_type=str(row["mime_type"] or "audio/wav"),
        )

    def upsert(
        self,
        term: str,
        audio_bytes: bytes,
        mime_type: str,
        provider: str | None,
        model: str | None,
    ) -> None:
        with get_connection(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO presaved_words_audio (term, audio, mime_type, provider, model, generated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(term) DO UPDATE SET
                    audio = excluded.audio,
                    mime_type = excluded.mime_type,
                    provider = excluded.provider,
                    model = excluded.model,
                    generated_at = CURRENT_TIMESTAMP
                """,
                (term.strip().lower(), audio_bytes, mime_type, provider, model),
            )
