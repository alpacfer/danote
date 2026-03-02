from __future__ import annotations

import base64
import io
import time
import wave
from dataclasses import dataclass, field
from typing import Protocol


class TTSError(RuntimeError):
    """Raised when a text-to-speech provider fails."""


@dataclass
class PronunciationAudio:
    audio_bytes: bytes
    mime_type: str


class TTSService(Protocol):
    provider: str
    model: str

    def synthesize(self, text: str) -> PronunciationAudio | None: ...


@dataclass
class GeminiTTSService:
    """Gemini-based text-to-speech service.

    The Gemini TTS endpoint returns PCM payloads. This service converts PCM to WAV
    so the frontend can play it directly with the browser audio element.
    """

    api_key: str
    model: str = "gemini-2.5-flash-preview-tts"
    voice_name: str = "Kore"
    language_hint: str = "da-DK"
    timeout_seconds: float = 20.0
    max_retries: int = 2
    backoff_seconds: float = 0.5
    provider: str = field(default="gemini_tts", init=False)
    _client: object | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        normalized_key = self.api_key.strip()
        normalized_model = self.model.strip()
        normalized_voice = self.voice_name.strip()
        normalized_language_hint = self.language_hint.strip()
        if not normalized_key:
            raise TTSError("Gemini API key is required for text-to-speech.")
        if not normalized_model:
            raise TTSError("Gemini TTS model is required.")
        if not normalized_voice:
            raise TTSError("Gemini TTS voice name is required.")
        if not normalized_language_hint:
            raise TTSError("Gemini TTS language hint is required.")
        self.api_key = normalized_key
        self.model = normalized_model
        self.voice_name = normalized_voice
        self.language_hint = normalized_language_hint

    def _ensure_client(self) -> object:
        if self._client is None:
            try:
                from google import genai  # type: ignore import-not-found
            except ImportError as exc:
                raise TTSError("google-genai package is required for Gemini text-to-speech.") from exc
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def close(self) -> None:
        self._client = None

    def synthesize(self, text: str) -> PronunciationAudio | None:
        normalized = text.strip()
        if not normalized:
            return None

        attempts = self.max_retries + 1
        for attempt in range(attempts):
            try:
                from google.genai import types  # type: ignore import-not-found

                client = self._ensure_client()
                prompt = self._build_pronunciation_prompt(normalized)
                response = client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=["AUDIO"],
                        speech_config=types.SpeechConfig(
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                    voice_name=self.voice_name,
                                )
                            )
                        ),
                    ),
                )
                audio_payload = self._extract_audio_payload(response)
                if not audio_payload:
                    return None
                audio_bytes, mime_type = audio_payload
                if mime_type in {"audio/wav", "audio/x-wav"}:
                    return PronunciationAudio(audio_bytes=audio_bytes, mime_type="audio/wav")
                if mime_type and mime_type.startswith("audio/") and mime_type not in {"audio/pcm", "audio/l16"}:
                    return PronunciationAudio(audio_bytes=audio_bytes, mime_type=mime_type)
                wav_bytes = self._pcm_to_wav_bytes(audio_bytes)
                return PronunciationAudio(audio_bytes=wav_bytes, mime_type="audio/wav")
            except Exception as exc:
                if attempt < self.max_retries:
                    delay = self.backoff_seconds * (2**attempt)
                    if delay > 0:
                        time.sleep(delay)
                    continue
                raise TTSError(f"Gemini TTS request failed: {exc}") from exc

        return None

    def _build_pronunciation_prompt(self, word: str) -> str:
        return (
            f"The target language is Danish ({self.language_hint}). "
            "Pronounce the exact token naturally in Danish.\n"
            "Rules:\n"
            "- Do not translate.\n"
            "- Do not add any other words.\n"
            "- Do not spell letters.\n"
            "- Speak the token once.\n"
            f"Token: {word}"
        )

    @staticmethod
    def _extract_audio_payload(response: object) -> tuple[bytes, str | None] | None:
        candidates = getattr(response, "candidates", None)
        if not isinstance(candidates, list) or not candidates:
            return None
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None)
            if not isinstance(parts, list) or not parts:
                continue
            for part in parts:
                inline_data = getattr(part, "inline_data", None)
                if inline_data is None:
                    continue
                data = getattr(inline_data, "data", None)
                mime_type = getattr(inline_data, "mime_type", None)
                normalized_mime = mime_type.strip().lower() if isinstance(mime_type, str) and mime_type.strip() else None
                if isinstance(data, bytes) and data:
                    return data, normalized_mime
                if isinstance(data, str):
                    try:
                        decoded = base64.b64decode(data)
                        if decoded:
                            return decoded, normalized_mime
                    except Exception:
                        continue
        return None

    @staticmethod
    def _pcm_to_wav_bytes(pcm_data: bytes, *, channels: int = 1, rate: int = 24000, sample_width: int = 2) -> bytes:
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(rate)
            wav_file.writeframes(pcm_data)
        return buffer.getvalue()
