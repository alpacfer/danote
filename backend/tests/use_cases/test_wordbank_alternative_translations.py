from pathlib import Path

from app.services.use_cases.wordbank import WordbankUseCase
from tests.helpers.factories import _db_path
from tests.helpers.fakes import FakeGeminiWordTranslationService


def test_find_alternative_translations_updates_primary_meaning_translation_and_adds_alternatives(
    tmp_path: Path,
) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        gemini_word_translation_service=FakeGeminiWordTranslationService(
            {},
            alternative_overrides={
                ("plads", "plads", "space", "seat"): ("place", ["spot", "seat"])
            },
        ),
    )

    added = use_case.add_word(
        "plads",
        "plads",
        search_seed={
            "lemma": "plads",
            "surface": "plads",
            "meaning_key": "space",
            "gloss": "space",
            "english_translation": "seat",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Sing|Definite=Ind",
        },
    )
    assert added.meaning is not None

    response = use_case.find_alternative_translations("plads", meaning_id=added.meaning.id)
    details = use_case.get_lemma_details("plads")

    assert response.status == "updated"
    assert response.primary_translation == "place"
    assert response.added_additional_translations == ["spot", "seat"]
    assert details.meaning_sections[0].english_translation == "place"
    assert details.meaning_sections[0].additional_translations == ["spot", "seat"]


def test_find_alternative_translations_reports_missing_gemini_service(tmp_path: Path) -> None:
    use_case = WordbankUseCase(_db_path(tmp_path))
    use_case.add_word("bog", "bog", pos_tag="NOUN", morphology="Gender=Com|Number=Sing|Definite=Ind")

    response = use_case.find_alternative_translations("bog")

    assert response.status == "error"
    assert response.primary_translation is None
    assert response.added_additional_translations == []
