from __future__ import annotations

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
class AzureSpeechTTSService:
    """Azure Speech based text-to-speech service."""

    api_key: str
    region: str
    endpoint: str | None = None
    voice_name: str = "da-DK-ChristelNeural"
    model: str = "azure-speech-tts"
    provider: str = field(default="azure_speech_tts", init=False)

    def __post_init__(self) -> None:
        normalized_key = self.api_key.strip()
        normalized_region = self.region.strip()
        normalized_voice = self.voice_name.strip()
        if not normalized_key:
            raise TTSError("Azure Speech API key is required for text-to-speech.")
        if not normalized_region:
            raise TTSError("Azure Speech region is required for text-to-speech.")
        if not normalized_voice:
            raise TTSError("Azure Speech voice name is required for text-to-speech.")
        self.api_key = normalized_key
        self.region = normalized_region
        self.voice_name = normalized_voice
        self.endpoint = self.endpoint.strip() if isinstance(self.endpoint, str) and self.endpoint.strip() else None

    def close(self) -> None:
        # SDK resources are scoped per request in synthesize.
        return None

    def synthesize(self, text: str) -> PronunciationAudio | None:
        normalized = text.strip()
        if not normalized:
            return None

        try:
            import azure.cognitiveservices.speech as speechsdk  # type: ignore import-not-found
        except ImportError as exc:
            raise TTSError("azure-cognitiveservices-speech package is required for Azure text-to-speech.") from exc

        try:
            if self.endpoint:
                speech_config = speechsdk.SpeechConfig(
                    subscription=self.api_key,
                    endpoint=self.endpoint,
                )
            else:
                speech_config = speechsdk.SpeechConfig(
                    subscription=self.api_key,
                    region=self.region,
                )
            speech_config.speech_synthesis_voice_name = self.voice_name
            speech_config.set_speech_synthesis_output_format(
                speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm
            )
            synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
            result = synthesizer.speak_text_async(normalized).get()
        except Exception as exc:
            raise TTSError(f"Azure Speech TTS request failed: {exc}") from exc

        reason = getattr(result, "reason", None)
        completed_reason = getattr(speechsdk.ResultReason, "SynthesizingAudioCompleted", None)
        canceled_reason = getattr(speechsdk.ResultReason, "Canceled", None)

        if reason == completed_reason:
            audio_bytes = bytes(getattr(result, "audio_data", b""))
            if not audio_bytes:
                return None
            return PronunciationAudio(audio_bytes=audio_bytes, mime_type="audio/wav")

        if reason == canceled_reason:
            cancellation = speechsdk.SpeechSynthesisCancellationDetails(result)
            details = getattr(cancellation, "error_details", "") or "unknown error"
            raise TTSError(f"Azure Speech synthesis canceled: {details}")

        return None
