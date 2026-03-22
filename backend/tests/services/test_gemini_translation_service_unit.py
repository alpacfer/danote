from __future__ import annotations

import pytest

from app.services.gemini_translation import (
    ContextualWordTranslationInput,
    GeminiFlashLiteWordTranslationService,
    GeminiTranslationError,
    MeaningSectionCandidateInput,
    MeaningSectionSelectionInput,
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


def _schema_to_dict(schema: object) -> dict[str, object]:
    if isinstance(schema, dict):
        return schema
    dump = getattr(schema, "model_dump", None)
    if callable(dump):
        dumped = dump(exclude_none=True)
        if isinstance(dumped, dict):
            return dumped
    return {}


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
    assert "single Danish lemma" in str(prompt)
    assert "Translate lemma_da, not surface_form_da." in str(prompt)


def test_gemini_word_translation_service_glossless_verb_prompt_uses_danish_infinitive_frame(monkeypatch) -> None:
    service = GeminiFlashLiteWordTranslationService(api_key="test-key")
    fake_client = _FakeClient([_FakeResponse('{"translation":"to drive"}')])
    monkeypatch.setattr(service, "_ensure_client", lambda: fake_client)

    translated = service.translate_word(
        ContextualWordTranslationInput(
            surface_form="bil",
            lemma="bile",
            pos_tag="VERB",
            morphology="Mood=Imp|VerbForm=Fin",
        )
    )

    assert translated == "to drive"
    prompt = str(fake_client.models.calls[0]["contents"])
    assert '"lemma_frame_da": "at bile"' in prompt
    assert "search-quality fallback after another translator returned a Danish-looking echo" in prompt
    assert "Do not copy the Danish lemma into English framing such as 'to bile'" in prompt


def test_gemini_word_translation_service_prompt_prioritizes_common_morphology_sense(monkeypatch) -> None:
    service = GeminiFlashLiteWordTranslationService(api_key="test-key")
    fake_client = _FakeClient([_FakeResponse('{"translation":"to bend"}')])
    monkeypatch.setattr(service, "_ensure_client", lambda: fake_client)

    translated = service.translate_word(
        ContextualWordTranslationInput(
            surface_form="bog",
            lemma="boge",
            pos_tag="VERB",
            morphology="Mood=Imp|VerbForm=Fin",
        )
    )

    assert translated == "to bend"
    prompt = str(fake_client.models.calls[0]["contents"])
    assert "Treat pos_tag and morphology as hard constraints for sense disambiguation." in prompt
    assert "choose the most common modern English meaning" in prompt
    assert "prefer 'to bend'/'to bow' over golf-specific 'to bogey'" in prompt


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


def test_gemini_word_translation_service_batch_prompt_prioritizes_common_morphology_sense(monkeypatch) -> None:
    service = GeminiFlashLiteWordTranslationService(api_key="test-key")
    fake_client = _FakeClient(
        [
            _FakeResponse(
                None,
                parsed={"items": [{"id": "0", "translation": "to bend"}]},
            )
        ]
    )
    monkeypatch.setattr(service, "_ensure_client", lambda: fake_client)

    translated = service.translate_words_batch(
        [
            ContextualWordTranslationInput(
                surface_form="bog",
                lemma="boge",
                pos_tag="VERB",
                morphology="Mood=Imp|VerbForm=Fin",
            )
        ]
    )

    assert translated == ["to bend"]
    prompt = str(fake_client.models.calls[0]["contents"])
    assert "Treat pos_tag and morphology as hard constraints for sense disambiguation." in prompt
    assert "choose the most common modern English meaning" in prompt
    assert "prefer 'to bend'/'to bow' over golf-specific 'to bogey'" in prompt


def test_gemini_word_translation_service_glossless_batch_prompt_uses_danish_infinitive_frame(monkeypatch) -> None:
    service = GeminiFlashLiteWordTranslationService(api_key="test-key")
    fake_client = _FakeClient(
        [
            _FakeResponse(
                None,
                parsed={"items": [{"id": "0", "translation": "to drive"}]},
            )
        ]
    )
    monkeypatch.setattr(service, "_ensure_client", lambda: fake_client)

    translated = service.translate_words_batch(
        [
            ContextualWordTranslationInput(
                surface_form="bil",
                lemma="bile",
                pos_tag="VERB",
                morphology="Mood=Imp|VerbForm=Fin",
            )
        ]
    )

    assert translated == ["to drive"]
    prompt = str(fake_client.models.calls[0]["contents"])
    assert '"lemma_frame_da": "at bile"' in prompt
    assert "search-quality fallbacks after another translator echoed the Danish lemma" in prompt
    assert "Do not copy the Danish lemma into English framing such as 'to bile'" in prompt


def test_gemini_word_translation_service_selects_existing_meaning_section(monkeypatch) -> None:
    service = GeminiFlashLiteWordTranslationService(api_key="test-key")
    fake_client = _FakeClient([_FakeResponse(None, parsed={"meaning_section_id": 2})])
    monkeypatch.setattr(service, "_ensure_client", lambda: fake_client)

    selected = service.select_meaning_section(
        MeaningSectionSelectionInput(
            surface_form="bogens",
            lemma="bog",
            meaning_candidates=[
                MeaningSectionCandidateInput(id=1, meaning_key="book", gloss="book"),
                MeaningSectionCandidateInput(id=2, meaning_key="swamp", gloss="swamp"),
            ],
        )
    )

    assert selected == 2
    prompt = str(fake_client.models.calls[0]["contents"])
    assert "meaning_section_id" in prompt
    assert "Meaning sections" in prompt


def test_gemini_word_translation_service_returns_none_for_invalid_meaning_section(monkeypatch) -> None:
    service = GeminiFlashLiteWordTranslationService(api_key="test-key")
    fake_client = _FakeClient([_FakeResponse(None, parsed={"meaning_section_id": 99})])
    monkeypatch.setattr(service, "_ensure_client", lambda: fake_client)

    selected = service.select_meaning_section(
        MeaningSectionSelectionInput(
            surface_form="bogens",
            lemma="bog",
            meaning_candidates=[
                MeaningSectionCandidateInput(id=1, meaning_key="book", gloss="book"),
                MeaningSectionCandidateInput(id=2, meaning_key="swamp", gloss="swamp"),
            ],
        )
    )

    assert selected is None


def test_gemini_word_translation_service_uses_nullable_batch_schema() -> None:
    service = GeminiFlashLiteWordTranslationService(api_key="test-key")

    config = service._batch_response_config(item_count=2)
    schema = _schema_to_dict(getattr(config, "response_schema", {}))
    translation_schema = (
        schema.get("properties", {})
        .get("items", {})
        .get("items", {})
        .get("properties", {})
        .get("translation", {})
    )
    assert str(translation_schema.get("type", "")).upper().endswith("STRING")
    assert translation_schema.get("nullable") is True


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


def test_gemini_word_translation_service_does_not_retry_on_validation_errors(monkeypatch) -> None:
    service = GeminiFlashLiteWordTranslationService(api_key="test-key", max_retries=1)
    fake_client = _FakeClient([ValueError("schema validation failed"), _FakeResponse('{"translation":"book"}')])
    monkeypatch.setattr(service, "_ensure_client", lambda: fake_client)
    monkeypatch.setattr("app.services.gemini_translation.time.sleep", lambda _seconds: None)

    with pytest.raises(GeminiTranslationError):
        service.translate_word(
            ContextualWordTranslationInput(
                surface_form="bogen",
                lemma="bog",
                gloss="book",
            )
        )

    assert len(fake_client.models.calls) == 1


def test_gemini_word_translation_service_retries_on_transient_errors(monkeypatch) -> None:
    service = GeminiFlashLiteWordTranslationService(api_key="test-key", max_retries=1)
    fake_client = _FakeClient([RuntimeError("429 rate limit"), _FakeResponse('{"translation":"book"}')])
    monkeypatch.setattr(service, "_ensure_client", lambda: fake_client)
    monkeypatch.setattr("app.services.gemini_translation.time.sleep", lambda _seconds: None)

    translated = service.translate_word(
        ContextualWordTranslationInput(
            surface_form="bogen",
            lemma="bog",
            gloss="book",
        )
    )

    assert translated == "book"
    assert len(fake_client.models.calls) == 2


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


def test_gemini_word_translation_service_sets_client_timeout(monkeypatch) -> None:
    from google import genai

    captured: dict[str, object] = {}

    class _StubClient:
        def __init__(self, *, api_key: str, http_options):
            captured["api_key"] = api_key
            captured["http_options"] = http_options
            self.models = _FakeModels([_FakeResponse('{"translation":"book"}')])

    monkeypatch.setattr(genai, "Client", _StubClient)
    service = GeminiFlashLiteWordTranslationService(api_key="test-key", timeout_seconds=7.5)

    translated = service.translate_word(
        ContextualWordTranslationInput(
            surface_form="bogen",
            lemma="bog",
            gloss="book",
        )
    )

    timeout = getattr(captured.get("http_options"), "timeout", None)
    assert translated == "book"
    assert captured["api_key"] == "test-key"
    assert timeout == 7500
