from __future__ import annotations

from app.services.verification import GeminiWordVerificationService, WordVerificationInput


def _payload() -> WordVerificationInput:
    return WordVerificationInput(
        stored_lemma="bog",
        stored_surface_form="bogen",
        meaning_id=1,
        meaning_key="book",
        meaning_gloss="book",
        lexeme_source="manual",
        lexeme_translation="book",
        lexeme_translation_provider="meaning_section",
        surface_source="manual",
        lemma_pos_tag="NOUN",
        lemma_morphology="Gender=Com|Number=Sing",
        surface_pos_tag="NOUN",
        surface_morphology="Definite=Def|Number=Sing",
        sibling_meaning_sections=(),
    )


def test_gemini_verification_service_keeps_only_supported_actions(monkeypatch) -> None:
    service = GeminiWordVerificationService(api_key="test-key")
    monkeypatch.setattr(
        service,
        "_generate_text",
        lambda prompt: (
            '{"verdict":"incorrect","word_count":1,"problem":"mismatch","change_to_implement":"fix it",'
            '"suggested_actions":['
            '{"action_type":"fix_translation","english_translation":"book","reason":"translation mismatch"},'
            '{"action_type":"rename_everything","target":"ignored"}'
            ']}'
        ),
    )

    result = service.verify_word_entry(_payload())

    assert result.verdict == "flagged"
    assert [action.action_type for action in result.suggested_actions] == ["fix_translation"]
    assert result.suggested_actions[0].english_translation == "book"


def test_gemini_verification_service_discards_malformed_actions(monkeypatch) -> None:
    service = GeminiWordVerificationService(api_key="test-key")
    monkeypatch.setattr(
        service,
        "_generate_text",
        lambda prompt: (
            '{"verdict":"incorrect","word_count":1,"problem":"mismatch","change_to_implement":"fix it",'
            '"suggested_actions":['
            '{"action_type":"move_to_meaning_section"},'
            '{"action_type":"move_to_lemma","target_lemma":"bind"}'
            ']}'
        ),
    )

    result = service.verify_word_entry(_payload())

    assert result.verdict == "flagged"
    assert result.suggested_actions == ()
