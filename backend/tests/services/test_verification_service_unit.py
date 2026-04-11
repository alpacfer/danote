from __future__ import annotations

from dataclasses import replace

from app.services.verification import (
    GeminiWordVerificationService,
    WordVerificationInput,
    WordVerificationMeaningSection,
    WordVerificationSurfaceForm,
)
from app.services.verification_paradigm_slots import build_completion_review_paradigm_slot_context


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


def _mor_person_payload(
    *,
    review_intent: str = "general",
) -> WordVerificationInput:
    return WordVerificationInput(
        stored_lemma="mor",
        stored_surface_form=None,
        meaning_id=1,
        meaning_key="person",
        meaning_gloss="person",
        meaning_gloss_translation="person",
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
                id=2,
                meaning_key="soil-layer",
                gloss="jordlag",
                gloss_translation="soil layer",
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


def _verb_payload(
    *,
    review_intent: str = "general",
) -> WordVerificationInput:
    return WordVerificationInput(
        stored_lemma="lære",
        stored_surface_form=None,
        meaning_id=3,
        meaning_key="learn",
        meaning_gloss="learn",
        meaning_gloss_translation="learn",
        lexeme_source="search",
        selected_translation="learn",
        selected_translation_scope="meaning_section",
        surface_source=None,
        canonical_lemma="lære",
        canonical_lemma_pos_tag="VERB",
        canonical_lemma_morphology="VerbForm=Inf|Voice=Act",
        selected_meaning_pos_tag="VERB",
        selected_meaning_morphology="VerbForm=Inf|Voice=Act",
        selected_surface_pos_tag=None,
        selected_surface_morphology=None,
        available_surface_forms=(
            WordVerificationSurfaceForm(
                form="lærer",
                meaning_id=3,
                meaning_key="learn",
                gloss="learn",
                gloss_translation="learn",
                english_translation="learn",
                pos_tag="VERB",
                morphology="Tense=Pres|VerbForm=Fin|Voice=Act",
                source="search",
                gram_raw="vb.præs.akt",
            ),
            WordVerificationSurfaceForm(
                form="kom",
                meaning_id=3,
                meaning_key="learn",
                gloss="learn",
                gloss_translation="learn",
                english_translation="learn",
                pos_tag="VERB",
                morphology="Tense=Past|VerbForm=Fin",
                source="search",
                gram_raw="vb.præt.akt | vb.imp",
            ),
            WordVerificationSurfaceForm(
                form="lært",
                meaning_id=3,
                meaning_key="learn",
                gloss="learn",
                gloss_translation="learn",
                english_translation="learn",
                pos_tag="VERB",
                morphology="VerbForm=Part|Voice=Act",
                source="search",
                gram_raw="vb.perf.part",
            ),
        ),
        review_intent=review_intent,
    )


def _bile_payload(
    *,
    stored_surface_form: str | None = None,
    selected_translation: str | None = None,
) -> WordVerificationInput:
    return WordVerificationInput(
        stored_lemma="bile",
        stored_surface_form=stored_surface_form,
        meaning_id=10,
        meaning_key="bile",
        meaning_gloss="køre i bil",
        meaning_gloss_translation="go by car",
        lexeme_source="search",
        selected_translation=selected_translation,
        selected_translation_scope="meaning_section" if selected_translation else None,
        surface_source="search" if stored_surface_form else None,
        canonical_lemma="bile",
        canonical_lemma_pos_tag="VERB",
        canonical_lemma_morphology="VerbForm=Inf|Voice=Act",
        selected_meaning_pos_tag="VERB",
        selected_meaning_morphology="VerbForm=Inf|Voice=Act",
        selected_surface_pos_tag="VERB" if stored_surface_form else None,
        selected_surface_morphology="Mood=Imp|VerbForm=Fin" if stored_surface_form else None,
        sibling_meaning_sections=(),
        available_surface_forms=(
            WordVerificationSurfaceForm(
                form="bil",
                meaning_id=10,
                meaning_key="bile",
                gloss="køre i bil",
                gloss_translation="go by car",
                english_translation=None,
                pos_tag="VERB",
                morphology="Mood=Imp|VerbForm=Fin",
                source="search",
                gram_raw="vb.imp",
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
            '{"action_type":"fix_variations","reason":"replace the completed forms",'
            '"singular_indefinite_forms":["mor","moder"],'
            '"singular_definite_forms":["moren"],'
            '"plural_indefinite_forms":["mødre"],'
            '"plural_definite_forms":["mødrene"]},'
            '{"action_type":"rename_everything","target":"ignored"}'
            ']}'
        ),
    )

    result = service.verify_word_entry(replace(_payload(), review_intent="complete_variations"))

    assert result.verdict == "flagged"
    assert [action.action_type for action in result.suggested_actions] == ["fix_variations"]
    assert result.suggested_actions[0].singular_indefinite_forms == ("mor", "moder")
    assert result.suggested_actions[0].plural_indefinite_forms == ("mødre",)
    assert result.suggested_actions[0].plural_definite_forms == ("mødrene",)


def test_gemini_complete_variations_discards_non_variation_actions(monkeypatch) -> None:
    service = GeminiWordVerificationService(api_key="test-key")
    monkeypatch.setattr(
        service,
        "_generate_text",
        lambda prompt: (
            '{"verdict":"incorrect","word_count":1,"problem":"mismatch","change_to_implement":"fix it",'
            '"suggested_actions":['
            '{"action_type":"fix_translation","english_translation":"mother","reason":"ignored"},'
            '{"action_type":"move_to_meaning_section","target_meaning_id":1,"reason":"ignored"},'
            '{"action_type":"move_to_lemma","target_lemma":"moder","target_meaning_key":"person","reason":"ignored"}'
            ']}'
        ),
    )

    result = service.verify_word_entry(_mor_payload(review_intent="complete_variations"))

    assert result.verdict == "flagged"
    assert result.suggested_actions == ()


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


def test_gemini_verification_service_allows_fix_translation_for_meaning_reviews(monkeypatch) -> None:
    service = GeminiWordVerificationService(api_key="test-key")
    monkeypatch.setattr(
        service,
        "_generate_text",
        lambda prompt: (
            '{"verdict":"incorrect","word_count":1,"problem":"translation mismatch","change_to_implement":"set translation",'
            '"suggested_actions":['
            '{"action_type":"fix_translation","english_translation":"mother","reason":"use the noun translation"}'
            ']}'
        ),
    )

    result = service.verify_word_entry(_mor_payload())

    assert result.verdict == "flagged"
    assert [action.action_type for action in result.suggested_actions] == ["fix_translation"]
    assert result.suggested_actions[0].english_translation == "mother"
    assert result.problem == "The English translation does not match the saved meaning."
    assert result.change_to_implement == "Set the translation to the saved meaning."


def test_gemini_verification_service_ignores_gloss_translation_substitution_for_valid_saved_translation(
    monkeypatch,
) -> None:
    service = GeminiWordVerificationService(api_key="test-key")
    monkeypatch.setattr(
        service,
        "_generate_text",
        lambda prompt: (
            '{"verdict":"incorrect","word_count":1,"problem":"translation mismatch","change_to_implement":"set translation",'
            '"suggested_actions":['
            '{"action_type":"fix_translation","english_translation":"person","reason":"use the gloss translation"}'
            ']}'
        ),
    )

    result = service.verify_word_entry(_mor_person_payload())

    assert result.verdict == "verified"
    assert result.suggested_actions == ()


def test_gemini_verification_service_rewrites_gloss_critique_as_translation_review(monkeypatch) -> None:
    service = GeminiWordVerificationService(api_key="test-key")
    monkeypatch.setattr(
        service,
        "_generate_text",
        lambda prompt: (
            '{"verdict":"incorrect","word_count":1,'
            '"problem":"The gloss \'person\' is too generic and inaccurate for the lemma.",'
            '"change_to_implement":"Update the gloss-aware translation.",'
            '"suggested_actions":['
            '{"action_type":"fix_translation","english_translation":"mother","reason":"use the noun translation"}'
            ']}'
        ),
    )

    result = service.verify_word_entry(_mor_payload())

    assert result.verdict == "flagged"
    assert [action.action_type for action in result.suggested_actions] == ["fix_translation"]
    assert result.problem == "The English translation does not match the saved meaning."
    assert result.change_to_implement == "Set the translation to the saved meaning."


def test_gemini_verification_service_discards_fix_translation_for_surface_reviews(monkeypatch) -> None:
    service = GeminiWordVerificationService(api_key="test-key")
    monkeypatch.setattr(
        service,
        "_generate_text",
        lambda prompt: (
            '{"verdict":"incorrect","word_count":1,"problem":"translation mismatch","change_to_implement":"set translation",'
            '"suggested_actions":['
            '{"action_type":"fix_translation","english_translation":"book","reason":"ignored"}'
            ']}'
        ),
    )

    result = service.verify_word_entry(_payload())

    assert result.verdict == "verified"
    assert result.suggested_actions == ()


def test_gemini_verification_service_ignores_gloss_only_review_without_actions(monkeypatch) -> None:
    service = GeminiWordVerificationService(api_key="test-key")
    monkeypatch.setattr(
        service,
        "_generate_text",
        lambda prompt: (
            '{"verdict":"incorrect","word_count":1,'
            '"problem":"The gloss \'person\' is too broad for this lemma.",'
            '"change_to_implement":"Replace the gloss with a better sense label.",'
            '"suggested_actions":[]}'
        ),
    )

    result = service.verify_word_entry(_mor_payload())

    assert result.verdict == "verified"
    assert result.suggested_actions == ()


def test_gemini_verification_service_ignores_surface_translation_only_prose(monkeypatch) -> None:
    service = GeminiWordVerificationService(api_key="test-key")
    monkeypatch.setattr(
        service,
        "_generate_text",
        lambda prompt: (
            '{"verdict":"incorrect","word_count":1,"problem":"Translation is wrong.","change_to_implement":"Set translation to book.",'
            '"suggested_actions":[]}'
        ),
    )

    result = service.verify_word_entry(_payload())

    assert result.verdict == "verified"
    assert result.suggested_actions == ()


def test_gemini_verification_prompt_matches_wordbank_translation_model() -> None:
    service = GeminiWordVerificationService(api_key="test-key")

    payload = _payload()
    prompt = service._verification_prompt(payload)
    category_prompt = service._category_prompt(payload)

    assert "Translations belong to the lemma or meaning section only" in prompt
    assert "Surface forms do not have independent translations" in prompt
    assert "Never suggest editing a gloss" in prompt
    assert "Treat glosses and gloss translations as fixed COR reference labels" in prompt
    assert "Only review whether the saved English translation fits the saved lemma or meaning" in prompt
    assert "Use the reviewed target, relevant surface forms, and sibling meanings only as needed" in prompt
    assert "If canonical_lemma is present and differs from lemma" in prompt
    assert "idiomatic English" in prompt
    assert "meaning_gloss_translation" in prompt
    assert "gloss_translation" in prompt
    assert "available_categories" not in prompt
    assert "current_categories" not in prompt
    assert "relevant_surface_forms" in prompt
    assert "paradigm_slot_surface_forms" in prompt
    assert '"gram_raw": null' in prompt
    assert '"canonical_lemma": "bog"' in prompt
    assert '"gloss": "book"' in prompt
    assert '"morphology": "Definite=Def|Number=Sing"' in prompt
    assert "new_categories" not in prompt
    assert "Do not require missing paradigm forms" in prompt
    assert "Variation completeness is handled only by the Complete variations workflow" in prompt
    assert "fix_variations" not in prompt
    assert "Do not suggest translation fixes for this scope" in prompt
    assert "Homographs are common" in prompt
    assert '{"action_type":"fix_translation"' not in prompt
    assert "available_categories" in category_prompt
    assert "current_categories" in category_prompt
    assert "relevant_surface_forms" in category_prompt


def test_gemini_meaning_review_prompt_keeps_translation_actions_available() -> None:
    service = GeminiWordVerificationService(api_key="test-key")

    prompt = service._verification_prompt(_bile_payload(selected_translation="to bile"))

    assert "Translation fixes may apply only at this scope" in prompt
    assert '{"action_type":"fix_translation"' in prompt
    assert '{"action_type":"move_to_meaning_section"' not in prompt
    assert '"translation_hint": "go by car"' in prompt
    assert '"gram_raw": "vb.imp"' in prompt


def test_gemini_verification_service_discards_move_to_lemma_for_supported_imperative_surface_reviews(monkeypatch) -> None:
    service = GeminiWordVerificationService(api_key="test-key")
    monkeypatch.setattr(
        service,
        "_generate_text",
        lambda prompt: (
            '{"verdict":"incorrect","word_count":1,"problem":"noun mismatch","change_to_implement":"move the entry",'
            '"suggested_actions":['
            '{"action_type":"move_to_lemma","target_lemma":"bil","target_meaning_key":"car","reason":"homograph confusion"}'
            ']}'
        ),
    )

    result = service.verify_word_entry(_bile_payload(stored_surface_form="bil"))

    assert result.verdict == "verified"
    assert result.suggested_actions == ()


def test_gemini_verification_service_backfills_translation_when_move_to_lemma_conflicts_with_supported_paradigm(
    monkeypatch,
) -> None:
    service = GeminiWordVerificationService(api_key="test-key")
    monkeypatch.setattr(
        service,
        "_generate_text",
        lambda prompt: (
            '{"verdict":"incorrect","word_count":1,"problem":"move to noun lemma","change_to_implement":"move bile to bil",'
            '"suggested_actions":['
            '{"action_type":"move_to_lemma","target_lemma":"bil","target_meaning_key":"car","reason":"homograph confusion"}'
            ']}'
        ),
    )

    result = service.verify_word_entry(_bile_payload())

    assert result.verdict == "flagged"
    assert [action.action_type for action in result.suggested_actions] == ["fix_translation"]
    assert result.suggested_actions[0].english_translation == "go by car"


def test_gemini_verification_service_flags_missing_meaning_translation_from_gloss_hint_even_when_provider_says_ok(
    monkeypatch,
) -> None:
    service = GeminiWordVerificationService(api_key="test-key")
    monkeypatch.setattr(
        service,
        "_generate_text",
        lambda prompt: '{"verdict":"correct","word_count":1,"suggested_actions":[]}',
    )

    result = service.verify_word_entry(_bile_payload())

    assert result.verdict == "flagged"
    assert [action.action_type for action in result.suggested_actions] == ["fix_translation"]
    assert result.suggested_actions[0].english_translation == "go by car"


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
    assert "Use only this action type: fix_variations" in prompt
    assert "fix_variations" in prompt
    assert "singular_indefinite_forms" in prompt
    assert "plural_indefinite_forms" in prompt
    assert "plural_definite_forms" in prompt
    assert "noun_slot_surface_forms" in prompt
    assert '{"action_type":"fix_translation"' not in prompt
    assert '{"action_type":"move_to_meaning_section"' not in prompt
    assert '{"action_type":"move_to_lemma"' not in prompt
    assert "suggest move_to_lemma to canonical_lemma" not in prompt


def test_gemini_complete_variations_prompt_includes_verb_slot_fields() -> None:
    service = GeminiWordVerificationService(api_key="test-key")

    prompt = service._verification_prompt(_verb_payload(review_intent="complete_variations"))

    assert "infinitive_forms" in prompt
    assert "present_forms" in prompt
    assert "past_forms" in prompt
    assert "imperative_forms" in prompt
    assert "past_participle_forms" in prompt


def test_completion_review_slot_context_uses_merged_gram_raw_for_shared_adjective_forms() -> None:
    payload = WordVerificationInput(
        stored_lemma="smuk",
        stored_surface_form=None,
        meaning_id=7,
        meaning_key="beautiful",
        meaning_gloss="beautiful",
        meaning_gloss_translation="beautiful",
        lexeme_source="search",
        selected_translation="beautiful",
        selected_translation_scope="meaning_section",
        surface_source=None,
        canonical_lemma="smuk",
        canonical_lemma_pos_tag="ADJ",
        canonical_lemma_morphology="Gender=Com|Number=Sing|Definite=Ind",
        selected_meaning_pos_tag="ADJ",
        selected_meaning_morphology="Gender=Com|Number=Sing|Definite=Ind",
        selected_surface_pos_tag=None,
        selected_surface_morphology=None,
        available_surface_forms=(
            WordVerificationSurfaceForm(
                form="smukt",
                meaning_id=7,
                meaning_key="beautiful",
                gloss="beautiful",
                gloss_translation="beautiful",
                english_translation="beautiful",
                pos_tag="ADJ",
                morphology="Gender=Neut|Number=Sing|Definite=Ind",
                source="search",
                gram_raw="adj.sg.ubest.itk",
            ),
            WordVerificationSurfaceForm(
                form="smukke",
                meaning_id=7,
                meaning_key="beautiful",
                gloss="beautiful",
                gloss_translation="beautiful",
                english_translation="beautiful",
                pos_tag="ADJ",
                morphology="Number=Sing|Definite=Def",
                source="search",
                gram_raw="adj.sg.best | adj.pl",
            ),
        ),
        review_intent="complete_variations",
    )

    slot_context = build_completion_review_paradigm_slot_context(payload)

    assert slot_context == {
        "singular_indefinite_n_word": ["smuk"],
        "singular_indefinite_t_word": ["smukt"],
        "singular_definite": ["smukke"],
        "plural_shared": ["smukke"],
        "plural_indefinite": ["smukke"],
        "plural_definite": ["smukke"],
    }


def test_completion_review_slot_context_uses_merged_gram_raw_for_shared_verb_forms() -> None:
    slot_context = build_completion_review_paradigm_slot_context(_verb_payload(review_intent="complete_variations"))

    assert slot_context == {
        "infinitive": ["lære"],
        "present": ["lærer"],
        "past": ["kom"],
        "imperative": ["kom"],
        "past_participle": ["lært"],
    }


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
            '"plural_indefinite_forms":["bøger"],"plural_definite_forms":["bøgerne"]}'
            ']}'
        ),
    )

    result = service.verify_word_entry(_payload())

    assert result.verdict == "verified"
    assert result.suggested_actions == ()


def test_gemini_category_classification_prefers_existing_and_one_new_category(monkeypatch) -> None:
    service = GeminiWordVerificationService(api_key="test-key")
    monkeypatch.setattr(
        service,
        "_generate_text",
        lambda prompt: (
            '{"existing_categories":["Household Objects","Food","Unknown"],'
            '"new_categories":["Reading Material","Culture","Education","Ignored"]'
            '}'
        ),
    )

    result = service.classify_word_categories(_payload())

    assert result.categories == ("Household Objects", "Food", "Reading Material")


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

    assert result.categories == ("Household Objects", "Reading Material")


def test_ensure_client_passes_timeout_to_http_options() -> None:
    """_ensure_client must wire timeout_seconds into genai.Client http_options."""
    import math
    import sys
    import types as _types

    captured: dict[str, object] = {}

    class _FakeHttpOptions:
        def __init__(self, *, timeout: int) -> None:
            self.timeout = timeout

    # Build fake google.genai.types as a proper module
    fake_genai_types = _types.ModuleType("google.genai.types")
    fake_genai_types.HttpOptions = _FakeHttpOptions  # type: ignore[attr-defined]

    class _FakeGenaiClient:
        def __init__(self, *, api_key: str, http_options: object) -> None:
            captured["http_options"] = http_options

    # Build fake google.genai as a proper module
    fake_genai = _types.ModuleType("google.genai")
    fake_genai.Client = _FakeGenaiClient  # type: ignore[attr-defined]
    fake_genai.types = fake_genai_types  # type: ignore[attr-defined]

    # Build fake google package as a proper module
    google_pkg = _types.ModuleType("google")
    google_pkg.genai = fake_genai  # type: ignore[attr-defined]

    orig = sys.modules.copy()
    sys.modules["google"] = google_pkg
    sys.modules["google.genai"] = fake_genai
    sys.modules["google.genai.types"] = fake_genai_types

    try:
        svc = GeminiWordVerificationService(api_key="key", timeout_seconds=15.0)
        svc._client = None  # force re-init
        svc._ensure_client()
    finally:
        sys.modules.clear()
        sys.modules.update(orig)

    http_options = captured.get("http_options")
    assert http_options is not None, "http_options not passed to genai.Client"
    expected_ms = max(1, math.ceil(15.0 * 1000))
    assert getattr(http_options, "timeout", None) == expected_ms


def test_word_verification_service_protocol_has_batch_method() -> None:
    from app.services.verification import WordVerificationService
    assert hasattr(WordVerificationService, "verify_word_entries_batch")


def test_gemini_batch_verification_returns_per_word_results(monkeypatch) -> None:
    service = GeminiWordVerificationService(api_key="test-key")
    monkeypatch.setattr(
        service,
        "_generate_content",
        lambda prompt, config=None: type("R", (), {
            "text": (
                '{"results":['
                '{"word_id":0,"verdict":"correct","word_count":1,"suggested_actions":[]},'
                '{"word_id":1,"verdict":"incorrect","word_count":1,"problem":"mismatch","change_to_implement":"fix","suggested_actions":[]}'
                ']}'
            ),
        })(),
    )

    results = service.verify_word_entries_batch([_payload(), _mor_payload()], sentence_context="test sentence")

    assert len(results) == 2
    assert results[0].verdict == "verified"
    assert results[1].verdict == "flagged"


def test_gemini_batch_verification_applies_post_processing_per_word(monkeypatch) -> None:
    service = GeminiWordVerificationService(api_key="test-key")
    monkeypatch.setattr(
        service,
        "_generate_content",
        lambda prompt, config=None: type("R", (), {
            "text": (
                '{"results":['
                '{"word_id":0,"verdict":"incorrect","word_count":1,"problem":"The gloss is wrong.","change_to_implement":"fix gloss","suggested_actions":[]},'
                '{"word_id":1,"verdict":"incorrect","word_count":1,"problem":"translation mismatch","change_to_implement":"set translation",'
                '"suggested_actions":[{"action_type":"fix_translation","english_translation":"mother","reason":"use the noun translation"}]}'
                ']}'
            ),
        })(),
    )

    results = service.verify_word_entries_batch([_payload(), _mor_payload()], sentence_context="test")

    assert results[0].verdict == "verified"  # gloss-only review suppressed
    assert results[0].suggested_actions == ()
    assert results[1].verdict == "flagged"  # translation fix allowed
    assert [a.action_type for a in results[1].suggested_actions] == ["fix_translation"]


def test_gemini_batch_verification_empty_payloads() -> None:
    service = GeminiWordVerificationService(api_key="test-key")
    assert service.verify_word_entries_batch([]) == []


def test_gemini_batch_verification_fallback_on_parse_failure(monkeypatch) -> None:
    service = GeminiWordVerificationService(api_key="test-key")
    monkeypatch.setattr(
        service,
        "_generate_content",
        lambda prompt, config=None: type("R", (), {"text": "not json"})(),
    )

    results = service.verify_word_entries_batch([_payload()])

    assert len(results) == 1
    assert results[0].verdict == "flagged"
    assert "Batch verification failed" in (results[0].problem or "")


def test_gemini_batch_verification_fallback_on_empty_response(monkeypatch) -> None:
    service = GeminiWordVerificationService(api_key="test-key")
    monkeypatch.setattr(
        service,
        "_generate_content",
        lambda prompt, config=None: type("R", (), {"text": ""})(),
    )

    results = service.verify_word_entries_batch([_payload()])

    assert len(results) == 1
    assert results[0].verdict == "flagged"
