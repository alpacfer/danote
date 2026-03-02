from __future__ import annotations

import sys
import types

import pytest

from app.services.tts import AzureSpeechTTSService, TTSError


def _install_fake_speechsdk(
    monkeypatch,
    *,
    reason: object,
    audio_data: bytes = b"",
    error_details: str = "",
    config_calls: list[dict] | None = None,
) -> None:
    module = types.ModuleType("azure.cognitiveservices.speech")

    class _ResultReason:
        SynthesizingAudioCompleted = "completed"
        Canceled = "canceled"

    class _SpeechSynthesisOutputFormat:
        Riff24Khz16BitMonoPcm = "riff24"

    class _SpeechConfig:
        def __init__(self, subscription=None, region=None, endpoint=None, **_kwargs):
            if config_calls is not None:
                config_calls.append(
                    {
                        "subscription": subscription,
                        "region": region,
                        "endpoint": endpoint,
                    }
                )
            self.subscription = subscription
            self.region = region
            self.endpoint = endpoint
            self.speech_synthesis_voice_name = None
            self.output_format = None

        def set_speech_synthesis_output_format(self, value):
            self.output_format = value

    class _Result:
        def __init__(self):
            self.reason = reason
            self.audio_data = audio_data

    class _Future:
        def get(self):
            return _Result()

    class _SpeechSynthesizer:
        def __init__(self, speech_config=None, audio_config=None):
            self.speech_config = speech_config
            self.audio_config = audio_config

        def speak_text_async(self, _text):
            return _Future()

    class _CancellationDetails:
        def __init__(self, _result):
            self.error_details = error_details

    module.ResultReason = _ResultReason
    module.SpeechSynthesisOutputFormat = _SpeechSynthesisOutputFormat
    module.SpeechConfig = _SpeechConfig
    module.SpeechSynthesizer = _SpeechSynthesizer
    module.SpeechSynthesisCancellationDetails = _CancellationDetails

    monkeypatch.setitem(sys.modules, "azure", types.ModuleType("azure"))
    monkeypatch.setitem(sys.modules, "azure.cognitiveservices", types.ModuleType("azure.cognitiveservices"))
    monkeypatch.setitem(sys.modules, "azure.cognitiveservices.speech", module)


def test_azure_speech_tts_requires_api_key_and_region() -> None:
    with pytest.raises(TTSError):
        AzureSpeechTTSService(api_key="", region="westeurope")
    with pytest.raises(TTSError):
        AzureSpeechTTSService(api_key="key", region="")


def test_azure_speech_tts_returns_wav_audio(monkeypatch) -> None:
    _install_fake_speechsdk(
        monkeypatch,
        reason="completed",
        audio_data=b"RIFFfakewav",
    )
    service = AzureSpeechTTSService(api_key="key", region="westeurope")
    audio = service.synthesize("katten")
    assert audio is not None
    assert audio.mime_type == "audio/wav"
    assert audio.audio_bytes == b"RIFFfakewav"


def test_azure_speech_tts_raises_on_canceled_result(monkeypatch) -> None:
    _install_fake_speechsdk(
        monkeypatch,
        reason="canceled",
        error_details="quota exceeded",
    )
    service = AzureSpeechTTSService(api_key="key", region="westeurope")
    with pytest.raises(TTSError):
        service.synthesize("katten")


def test_azure_speech_tts_uses_endpoint_without_region_when_endpoint_is_configured(monkeypatch) -> None:
    calls: list[dict] = []
    _install_fake_speechsdk(
        monkeypatch,
        reason="completed",
        audio_data=b"RIFFfakewav",
        config_calls=calls,
    )
    service = AzureSpeechTTSService(
        api_key="key",
        region="westeurope",
        endpoint="https://example.cognitiveservices.azure.com",
    )
    audio = service.synthesize("banan")
    assert audio is not None
    assert calls
    assert calls[0]["subscription"] == "key"
    assert calls[0]["endpoint"] == "https://example.cognitiveservices.azure.com"
    assert calls[0]["region"] is None
