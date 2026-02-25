from __future__ import annotations

import pytest

from app.services.translation import ArgosTranslationService, TranslationError


class _FakeTranslator:
    def __init__(self, output: str = "book", *, raises: Exception | None = None):
        self._output = output
        self._raises = raises

    def translate(self, _text: str) -> str:
        if self._raises is not None:
            raise self._raises
        return self._output


def test_translation_service_returns_translated_text(monkeypatch) -> None:
    service = ArgosTranslationService()
    monkeypatch.setattr(service, "_ensure_translator", lambda: _FakeTranslator("book"))
    assert service.translate_da_to_en("bog") == "book"


def test_translation_service_raises_on_transport_errors(monkeypatch) -> None:
    service = ArgosTranslationService()
    monkeypatch.setattr(service, "_ensure_translator", lambda: _FakeTranslator(raises=RuntimeError("bad model")))
    with pytest.raises(TranslationError):
        service.translate_da_to_en("bog")
