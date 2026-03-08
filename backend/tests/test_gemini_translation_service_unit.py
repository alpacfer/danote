from __future__ import annotations

import pytest

from app.services.gemini_translation import (
    ContextualWordTranslationInput,
    GeminiFlashLiteWordTranslationService,
    GeminiTranslationError,
)


class _FakeResponse:
    def __init__(self, text: str | None, *, parsed: object | None = None):
        self.text = text
        self.parsed = parsed


class _FakeModels:
    def __init__(self, sequence: list[object]):
        self._sequence = sequence
        self.calls: list[dict[str, object]] = []

    def generate_content(self, *, model: str, contents: str, config=None):
        self.calls.append({"model": model, "contents": contents, "config": config})
        event = self._sequence.pop(0)
        if isinstance(event, Exception):
            raise event
        return event


class _FakeClient:
    def __init__(self, sequence: list[object]):
        self.models = _FakeModels(sequence)


def test_gemini_word_translation_service_parses_json_response(monkeypatch) -> None:
    service = GeminiFlashLiteWordTranslationService(api_key="test-key")
    fake_client = _FakeClient([_FakeResponse('{"translation":"the book"}')])
    monkeypatch.setattr(service, "_ensure_client", lambda: fake_client)

    translated = service.translate_word(
        ContextualWordTranslationInput(
            surface_form="bogen",
            lemma="bog",
            pos_tag="NOUN",
            morphology="Gender=Com|Number=Sing|Definite=Def",
            gloss="book",
        )
    )

    assert translated == "the book"
    assert "surface_form_da" in fake_client.models.calls[0]["contents"]


def test_gemini_word_translation_service_handles_plain_text_response(monkeypatch) -> None:
    service = GeminiFlashLiteWordTranslationService(api_key="test-key")
    monkeypatch.setattr(service, "_ensure_client", lambda: _FakeClient([_FakeResponse("Learns")]))

    translated = service.translate_word(
        ContextualWordTranslationInput(
            surface_form="lærer",
            lemma="lære",
            pos_tag="VERB",
            morphology="Tense=Pres|VerbForm=Fin|Voice=Act",
            gloss="learn",
        )
    )

    assert translated == "learns"


def test_gemini_word_translation_service_supports_minimal_non_gloss_prompt(monkeypatch) -> None:
    service = GeminiFlashLiteWordTranslationService(api_key="test-key")
    fake_client = _FakeClient([_FakeResponse('{"translation":"more"}')])
    monkeypatch.setattr(service, "_ensure_client", lambda: fake_client)

    translated = service.translate_word(
        ContextualWordTranslationInput(
            surface_form="mere",
            lemma="mere",
        )
    )

    assert translated == "more"
    prompt = fake_client.models.calls[0]["contents"]
    assert "single Danish word" in str(prompt)


def test_gemini_word_translation_service_parses_structured_batch_response(monkeypatch) -> None:
    service = GeminiFlashLiteWordTranslationService(api_key="test-key")
    fake_client = _FakeClient(
        [
            _FakeResponse(
                None,
                parsed={
                    "items": [
                        {"id": "0", "translation": "the book"},
                        {"id": "1", "translation": "learns"},
                    ]
                },
            )
        ]
    )
    monkeypatch.setattr(service, "_ensure_client", lambda: fake_client)

    translated = service.translate_words_batch(
        [
            ContextualWordTranslationInput(surface_form="bogen", lemma="bog", gloss="book"),
            ContextualWordTranslationInput(surface_form="lærer", lemma="lære", gloss="learn"),
        ]
    )

    assert translated == ["the book", "learns"]
    assert fake_client.models.calls[0]["config"] is not None


def test_gemini_word_translation_service_parses_fenced_batch_json_response(monkeypatch) -> None:
    service = GeminiFlashLiteWordTranslationService(api_key="test-key")
    monkeypatch.setattr(
        service,
        "_ensure_client",
        lambda: _FakeClient(
            [
                _FakeResponse(
                    '```json\n{"items":[{"id":"0","translation":"the book"},{"id":"1","translation":""}]}\n```'
                )
            ]
        ),
    )

    translated = service.translate_words_batch(
        [
            ContextualWordTranslationInput(surface_form="bogen", lemma="bog", gloss="book"),
            ContextualWordTranslationInput(surface_form="tom", lemma="tom"),
        ]
    )

    assert translated == ["the book", None]


def test_gemini_word_translation_service_retries_then_raises(monkeypatch) -> None:
    service = GeminiFlashLiteWordTranslationService(api_key="test-key", max_retries=1)
    monkeypatch.setattr(
        service,
        "_ensure_client",
        lambda: _FakeClient([RuntimeError("boom"), RuntimeError("still-boom")]),
    )
    monkeypatch.setattr("app.services.gemini_translation.time.sleep", lambda _seconds: None)

    with pytest.raises(GeminiTranslationError):
        service.translate_word(
            ContextualWordTranslationInput(
                surface_form="bogen",
                lemma="bog",
                gloss="book",
            )
        )


def test_gemini_word_translation_service_batch_retries_then_raises(monkeypatch) -> None:
    service = GeminiFlashLiteWordTranslationService(api_key="test-key", max_retries=1)
    monkeypatch.setattr(
        service,
        "_ensure_client",
        lambda: _FakeClient([RuntimeError("boom"), RuntimeError("still-boom")]),
    )
    monkeypatch.setattr("app.services.gemini_translation.time.sleep", lambda _seconds: None)

    with pytest.raises(GeminiTranslationError):
        service.translate_words_batch(
            [
                ContextualWordTranslationInput(
                    surface_form="bogen",
                    lemma="bog",
                    gloss="book",
                )
            ]
        )
