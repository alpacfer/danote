from __future__ import annotations

from app.services.en_gemini_translation import ENGeminiTranslationService


class _FakeResponse:
    def __init__(self, text: str | None = None, *, parsed: object | None = None):
        self.text = text
        self.parsed = parsed


def test_en_gemini_describes_translation_choices_in_one_structured_call(monkeypatch) -> None:
    service = ENGeminiTranslationService(api_key="test-key")
    calls: list[dict[str, object]] = []

    def fake_generate_content(prompt: str, *, response_schema=None, max_output_tokens=64):
        calls.append({
            "prompt": prompt,
            "response_schema": response_schema,
            "max_output_tokens": max_output_tokens,
        })
        return _FakeResponse(parsed={
            "items": [
                {"id": "0", "description": "wax light"},
                {"id": "1", "description": "inspect eggs."},
                {"id": "ignored", "description": "skip me"},
            ],
        })

    monkeypatch.setattr(service, "_generate_content", fake_generate_content)

    descriptions = service.describe_translation_choices(
        query="candle",
        choices=[
            {
                "id": "0",
                "danish_translation": "lys",
                "pos_ud": "NOUN",
                "glosses": ["wax with a wick"],
            },
            {
                "id": "1",
                "danish_translation": "genlyse",
                "pos_ud": "VERB",
                "glosses": ["inspect an egg with light"],
            },
        ],
    )

    assert descriptions == {"0": "wax light", "1": "inspect eggs"}
    assert len(calls) == 1
    assert "English query: candle" in str(calls[0]["prompt"])
    assert calls[0]["response_schema"]["properties"]["items"]["type"] == "ARRAY"


def test_en_gemini_select_translation_matches_returns_id_to_bool(monkeypatch) -> None:
    service = ENGeminiTranslationService(api_key="test-key")
    captured: list[dict[str, object]] = []

    def fake_generate_content(prompt: str, *, response_schema=None, max_output_tokens=64):
        captured.append({"prompt": prompt, "response_schema": response_schema})
        return _FakeResponse(parsed={
            "items": [
                {"id": "0", "matches": True},
                {"id": "1", "matches": False},
                {"id": "ignored", "matches": True},
            ],
        })

    monkeypatch.setattr(service, "_generate_content", fake_generate_content)

    decisions = service.select_translation_matches(
        query="table",
        choices=[
            {
                "id": "0",
                "danish_lemma": "bord",
                "danish_gloss": "et møbel",
                "english_gloss": "a piece of furniture",
                "pos": "NOUN",
            },
            {
                "id": "1",
                "danish_lemma": "bord",
                "danish_gloss": "planke på skib el. båd",
                "english_gloss": "ship plank",
                "pos": "NOUN",
            },
        ],
    )

    assert decisions == {"0": True, "1": False}
    assert len(captured) == 1
    assert "English query: table" in str(captured[0]["prompt"])
    assert captured[0]["response_schema"]["properties"]["items"]["items"]["properties"]["matches"]["type"] == "BOOLEAN"


def test_en_gemini_select_translation_matches_returns_empty_for_empty_choices(monkeypatch) -> None:
    service = ENGeminiTranslationService(api_key="test-key")

    def fail_generate_content(prompt: str, *, response_schema=None, max_output_tokens=64):
        raise AssertionError("Gemini should not be called with empty choices")

    monkeypatch.setattr(service, "_generate_content", fail_generate_content)
    assert service.select_translation_matches(query="anything", choices=[]) == {}
