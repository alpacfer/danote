from __future__ import annotations

import io
import json
from urllib.error import URLError

import pytest

from app.services.translation import MyMemoryTranslationService, TranslationError


class _FakeResponse:
    def __init__(self, payload: dict):
        self._buffer = io.BytesIO(json.dumps(payload).encode("utf-8"))

    def read(self) -> bytes:
        return self._buffer.read()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None


def test_translation_service_returns_translated_text(monkeypatch) -> None:
    def _fake_urlopen(_url: str, timeout: float):
        assert timeout == 4.0
        return _FakeResponse({"responseData": {"translatedText": "book"}, "matches": []})

    monkeypatch.setattr("app.services.translation.urlopen", _fake_urlopen)

    service = MyMemoryTranslationService()
    assert service.translate_da_to_en("bog") == "book"


def test_translation_service_raises_on_transport_errors(monkeypatch) -> None:
    def _fake_urlopen(_url: str, timeout: float):
        raise URLError("no route")

    monkeypatch.setattr("app.services.translation.urlopen", _fake_urlopen)

    service = MyMemoryTranslationService()
    with pytest.raises(TranslationError):
        service.translate_da_to_en("bog")
