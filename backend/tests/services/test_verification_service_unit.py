from __future__ import annotations

from dataclasses import replace

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
        meaning_gloss_translation="book",
        lexeme_source="manual",
        selected_translation="book",
        selected_translation_scope="meaning_section",
        surface_source="manual",
        canonical_lemma="bog",
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
                gloss_translation="book",
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
                gloss_translation="book",
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
                gloss_translation="book",
                english_translation="book",
                pos_tag="NOUN",
                morphology="Definite=Def|Number=Sing",
                source="manual",
            ),
        ),
    )


def _mor_payload(
    *,
    review_intent: str = "general",
) -> WordVerificationInput:
    return WordVerificationInput(
        stored_lemma="mor",
        stored_surface_form=None,
        meaning_id=2,
        meaning_key="soil-layer",
        meaning_gloss="jordlag",
        meaning_gloss_translation="soil layer",
        lexeme_source="search",
        selected_translation="mother",
        selected_translation_scope="meaning_section",
        surface_source=None,
        canonical_lemma="moder",
        canonical_lemma_pos_tag="NOUN",
        canonical_lemma_morphology="Gender=Com|Number=Sing|Definite=Ind",
        selected_meaning_pos_tag="NOUN",
        selected_meaning_morphology="Gender=Com|Number=Sing|Definite=Ind",
        selected_surface_pos_tag=None,
        selected_surface_morphology=None,
        sibling_meaning_sections=(
            WordVerificationMeaningSection(
                id=1,
                meaning_key="person",
                gloss="person",
                gloss_translation="person",
                english_translation="mother",
                pos_tag="NOUN",
                morphology="Gender=Com|Number=Sing|Definite=Ind",
                surface_forms=("mor",),
            ),
        ),
        available_surface_forms=(
            WordVerificationSurfaceForm(
                form="mor",
                meaning_id=1,
                meaning_key="person",
                gloss="person",
                gloss_translation="person",
                english_translation="mother",
                pos_tag="NOUN",
                morphology="Gender=Com|Number=Sing|Definite=Ind",
                source="search",
            ),
            WordVerificationSurfaceForm(
                form="mor",
                meaning_id=2,
                meaning_key="soil-layer",
                gloss="jordlag",
                gloss_translation="soil layer",
                english_translation="mother",
                pos_tag="NOUN",
                morphology="Gender=Com|Number=Sing|Definite=Ind",
                source="search",
            ),
        ),
        review_intent=review_intent,
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
            '{"action_type":"fix_variations","reason":"replace the completed forms",'
            '"singular_definite_form":"moren","plural_indefinite_form":"mødre","plural_definite_form":"mødrene"},'
            '{"action_type":"fix_gloss","gloss":"reading material","reason":"should be ignored"},'
            '{"action_type":"rename_everything","target":"ignored"}'
            ']}'
        ),
    )

    result = service.verify_word_entry(replace(_payload(), review_intent="complete_variations"))

    assert result.verdict == "flagged"
    assert [action.action_type for action in result.suggested_actions] == ["fix_translation", "fix_variations"]
    assert result.suggested_actions[0].english_translation == "book"
    assert result.suggested_actions[1].plural_indefinite_form == "mødre"
    assert result.suggested_actions[1].plural_definite_form == "mødrene"


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


def test_gemini_verification_service_discards_danish_self_translation_actions(monkeypatch) -> None:
    service = GeminiWordVerificationService(api_key="test-key")
    monkeypatch.setattr(
        service,
        "_generate_text",
        lambda prompt: (
            '{"verdict":"incorrect","word_count":1,"problem":"mismatch","change_to_implement":"fix it",'
            '"suggested_actions":['
            '{"action_type":"fix_translation","english_translation":"mor","reason":"translation mismatch"}'
            ']}'
        ),
    )

    result = service.verify_word_entry(_mor_payload())

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
    assert "canonical lemma identity and metadata" in prompt
    assert "If canonical_lemma is present and differs from lemma" in prompt
    assert "Use all provided context together" in prompt
    assert "idiomatic English" in prompt
    assert "meaning_gloss_translation" in prompt
    assert "gloss_translation" in prompt
    assert "available_categories" in prompt
    assert "current_categories" in prompt
    assert "available_surface_forms" in prompt
    assert '"canonical_lemma": "bog"' in prompt
    assert '"gloss": "book"' in prompt
    assert '"morphology": "Definite=Def|Number=Sing"' in prompt
    assert "new_categories" in prompt
    assert "Do not require missing paradigm forms" in prompt
    assert "Variation completeness is handled only by the Complete variations workflow" in prompt
    assert "fix_variations" not in prompt
    assert "Use all provided context together" in category_prompt
    assert "available_surface_forms" in category_prompt


def test_gemini_verification_prompt_includes_canonical_lemma_mismatch_context() -> None:
    service = GeminiWordVerificationService(api_key="test-key")

    prompt = service._verification_prompt(_mor_payload())

    assert '"lemma": "mor"' in prompt
    assert '"canonical_lemma": "moder"' in prompt
    assert "suggest move_to_lemma to canonical_lemma" in prompt


def test_gemini_complete_variations_prompt_keeps_saved_lemma_fixed() -> None:
    service = GeminiWordVerificationService(api_key="test-key")

    prompt = service._verification_prompt(_mor_payload(review_intent="complete_variations"))

    assert '"review_intent": "complete_variations"' in prompt
    assert "Keep the saved lemma and meaning section fixed" in prompt
    assert "Do not suggest move_to_lemma solely because of that mismatch" in prompt
    assert "fix_variations" in prompt
    assert "plural_indefinite_form" in prompt
    assert "plural_definite_form" in prompt
    assert "suggest move_to_lemma to canonical_lemma" not in prompt


def test_gemini_general_verification_ignores_fix_variations_only_reviews(monkeypatch) -> None:
    service = GeminiWordVerificationService(api_key="test-key")
    monkeypatch.setattr(
        service,
        "_generate_text",
        lambda prompt: (
            '{"verdict":"incorrect","word_count":1,'
            '"problem":"Plural forms are missing.",'
            '"change_to_implement":"Add the missing plural forms.",'
            '"suggested_actions":['
            '{"action_type":"fix_variations","reason":"complete the paradigm",'
            '"plural_indefinite_form":"bøger","plural_definite_form":"bøgerne"}'
            ']}'
        ),
    )

    result = service.verify_word_entry(_payload())

    assert result.verdict == "verified"
    assert result.suggested_actions == ()


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
