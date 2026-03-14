from __future__ import annotations

from app.services.verification import (
    GeminiWordVerificationService,
    WordVerificationInput,
    WordVerificationMeaningSection,
    WordVerificationSurfaceForm,
)


def _payload() -> WordVerificationInput:
    return WordVerificationInput(
        stored_lemma="bog",
        stored_surface_form="bogen",
        meaning_id=1,
        meaning_key="book",
        meaning_gloss="book",
        lexeme_source="manual",
        selected_translation="book",
        selected_translation_scope="meaning_section",
        surface_source="manual",
        canonical_lemma_pos_tag="NOUN",
        canonical_lemma_morphology="Gender=Com|Number=Sing",
        selected_meaning_pos_tag="NOUN",
        selected_meaning_morphology="Gender=Com|Number=Sing",
        selected_surface_pos_tag="NOUN",
        selected_surface_morphology="Definite=Def|Number=Sing",
        current_categories=("Household Objects",),
        available_categories=("Animals", "Food", "Household Objects", "Plants"),
        sibling_meaning_sections=(
            WordVerificationMeaningSection(
                id=1,
                meaning_key="book",
                gloss="book",
                english_translation="book",
                pos_tag="NOUN",
                morphology="Gender=Com|Number=Sing",
                surface_forms=("bog", "bogen"),
            ),
        ),
        available_surface_forms=(
            WordVerificationSurfaceForm(
                form="bog",
                meaning_id=1,
                meaning_key="book",
                gloss="book",
                english_translation="book",
                pos_tag="NOUN",
                morphology="Gender=Com|Number=Sing",
                source="manual",
            ),
            WordVerificationSurfaceForm(
                form="bogen",
                meaning_id=1,
                meaning_key="book",
                gloss="book",
                english_translation="book",
                pos_tag="NOUN",
                morphology="Definite=Def|Number=Sing",
                source="manual",
            ),
        ),
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
            '{"action_type":"fix_gloss","gloss":"reading material","reason":"should be ignored"},'
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


def test_gemini_verification_prompt_matches_wordbank_translation_model() -> None:
    service = GeminiWordVerificationService(api_key="test-key")

    payload = _payload()
    prompt = service._verification_prompt(payload)
    category_prompt = service._category_prompt(payload)

    assert "lemma or a meaning section only" in prompt
    assert "Surface forms do not carry independent translations" in prompt
    assert "immutable COR labels" in prompt
    assert "Never suggest editing a gloss" in prompt
    assert "canonical lemma metadata" in prompt
    assert "Use all provided context together" in prompt
    assert "available_categories" in prompt
    assert "current_categories" in prompt
    assert "available_surface_forms" in prompt
    assert '"gloss": "book"' in prompt
    assert '"morphology": "Definite=Def|Number=Sing"' in prompt
    assert "new_categories" in prompt
    assert "Use all provided context together" in category_prompt
    assert "available_surface_forms" in category_prompt


def test_gemini_verification_service_parses_existing_and_up_to_three_new_categories(monkeypatch) -> None:
    service = GeminiWordVerificationService(api_key="test-key")
    monkeypatch.setattr(
        service,
        "_generate_text",
        lambda prompt: (
            '{"verdict":"correct","word_count":1,'
            '"existing_categories":["Household Objects","Food","Unknown"],'
            '"new_categories":["Reading Material","Culture","Education","Ignored"],'
            '"suggested_actions":[]}'
        ),
    )

    result = service.verify_word_entry(_payload())

    assert result.verdict == "verified"
    assert result.categories == ("Household Objects", "Food", "Reading Material", "Culture", "Education")


def test_gemini_category_classification_reuses_existing_and_new_categories(monkeypatch) -> None:
    service = GeminiWordVerificationService(api_key="test-key")
    monkeypatch.setattr(
        service,
        "_generate_text",
        lambda prompt: (
            '{"existing_categories":["Household Objects"],'
            '"new_categories":["Reading Material","Education","Culture"]}'
        ),
    )

    result = service.classify_word_categories(_payload())

    assert result.categories == ("Household Objects", "Reading Material", "Education", "Culture")
