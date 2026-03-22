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


def test_gemini_verification_prompt_matches_wordbank_translation_model() -> None:
    service = GeminiWordVerificationService(api_key="test-key")

    payload = _payload()
    prompt = service._verification_prompt(payload)
    category_prompt = service._category_prompt(payload)

    assert "Translations belong to the lemma or meaning section only" in prompt
    assert "Surface forms do not have independent translations" in prompt
    assert "Never suggest editing a gloss" in prompt
    assert "Use the reviewed target, relevant surface forms, and sibling meanings only as needed" in prompt
    assert "If canonical_lemma is present and differs from lemma" in prompt
    assert "idiomatic English" in prompt
    assert "meaning_gloss_translation" in prompt
    assert "gloss_translation" in prompt
    assert "available_categories" not in prompt
    assert "current_categories" not in prompt
    assert "relevant_surface_forms" in prompt
    assert '"canonical_lemma": "bog"' in prompt
    assert '"gloss": "book"' in prompt
    assert '"morphology": "Definite=Def|Number=Sing"' in prompt
    assert "new_categories" not in prompt
    assert "Do not require missing paradigm forms" in prompt
    assert "Variation completeness is handled only by the Complete variations workflow" in prompt
    assert "fix_variations" not in prompt
    assert "available_categories" in category_prompt
    assert "current_categories" in category_prompt
    assert "relevant_surface_forms" in category_prompt


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
