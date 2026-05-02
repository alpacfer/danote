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
