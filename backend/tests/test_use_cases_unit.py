from __future__ import annotations

from pathlib import Path

from app.db.migrations import apply_migrations
from app.services.use_cases.analyze import AnalyzeNoteUseCase
from app.services.use_cases.wordbank import WordbankUseCase
from app.nlp.adapter import NLPToken




class FakeTranslationService:
    def __init__(self, mapping: dict[str, str]):
        self._mapping = mapping

    def translate_da_to_en(self, text: str) -> str | None:
        return self._mapping.get(text)

class FakeNLPAdapter:
    def tokenize(self, text: str) -> list[NLPToken]:
        return [
            NLPToken(text="Hej", lemma="hej", pos=None, morphology=None, is_punctuation=False),
            NLPToken(text=",", lemma=None, pos=None, morphology=None, is_punctuation=True),
            NLPToken(text=" ", lemma=None, pos=None, morphology=None, is_punctuation=False),
            NLPToken(text="bog", lemma="bog", pos=None, morphology=None, is_punctuation=False),
        ]

    def lemma_candidates_for_token(self, token: str) -> list[str]:
        return [token.lower()]

    def lemma_for_token(self, token: str) -> str | None:
        return token.lower()

    def metadata(self) -> dict[str, str]:
        return {"adapter": "fake"}


def _db_path(tmp_path: Path) -> Path:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    return db_path


def test_wordbank_use_case_round_trip(tmp_path: Path) -> None:
    use_case = WordbankUseCase(_db_path(tmp_path))

    added = use_case.add_word("Bogen", "bog")
    assert added.status == "inserted"
    assert added.stored_lemma == "bog"
    assert added.stored_surface_form == "bogen"

    details = use_case.get_lemma_details("bog")
    assert details.lemma == "bog"
    assert details.surface_forms == ["bogen"]

    listing = use_case.list_lemmas()
    assert listing.items[0].lemma == "bog"
    assert listing.items[0].variation_count == 1
    assert listing.items[0].english_translation is None


def test_wordbank_use_case_stores_english_translation(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({"bog": "book"}),
    )

    use_case.add_word("Bogen", "bog")

    details = use_case.get_lemma_details("bog")
    assert details.english_translation == "book"


def test_analyze_use_case_filters_non_word_tokens(tmp_path: Path) -> None:
    use_case = AnalyzeNoteUseCase(
        _db_path(tmp_path),
        nlp_adapter=FakeNLPAdapter(),
        typo_engine=None,
    )

    tokens = use_case.execute("Hej, bog")
    surfaces = [token.surface_token for token in tokens]
    assert surfaces == ["Hej", "bog"]
