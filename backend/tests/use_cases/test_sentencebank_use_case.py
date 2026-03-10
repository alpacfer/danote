from __future__ import annotations

from pathlib import Path

from app.services.use_cases.sentencebank import SentencebankUseCase
from tests.helpers.factories import _db_path
from tests.helpers.fakes import (
    FakeTranslationService,
)


def test_sentencebank_use_case_add_and_list(tmp_path: Path) -> None:
    use_case = SentencebankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({"Jeg elsker dansk": "i love danish"}),
    )

    inserted = use_case.add_sentence("Jeg elsker dansk")
    duplicate = use_case.add_sentence("  jeg elsker   dansk ")
    listing = use_case.list_sentences()

    assert inserted.status == "inserted"
    assert inserted.source_text == "Jeg elsker dansk"
    assert inserted.english_translation == "i love danish"
    assert duplicate.status == "exists"
    assert listing.items[0].source_text == "Jeg elsker dansk"

def test_sentencebank_translation_is_normalized_to_lowercase(tmp_path: Path) -> None:
    use_case = SentencebankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({"Jeg elsker dansk": "I LOVE DANISH"}),
    )

    inserted = use_case.add_sentence("Jeg elsker dansk")

    assert inserted.status == "inserted"
    assert inserted.english_translation == "i love danish"

