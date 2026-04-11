from __future__ import annotations

import pytest

from app.services.use_cases.wordbank import WordbankUseCase
from tests.helpers.factories import _db_path, _cor_local_entry
from tests.helpers.fakes import FakeCORLocalLexiconService
from app.db.migrations import get_connection


def _add_word_directly(db_path, lemma: str) -> None:
    """Insert a minimal lexeme row for testing."""
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO lexemes (lemma, english_translation) VALUES (?, ?)",
            (lemma, None),
        )


def test_search_returns_did_you_mean_when_typo(tmp_path):
    db = _db_path(tmp_path)
    _add_word_directly(db, "hus")
    cor_local = FakeCORLocalLexiconService()
    use_case = WordbankUseCase(db, cor_local_lexicon_service=cor_local)

    result = use_case.search_lemmas("huse")

    assert result.did_you_mean == "hus"
    assert any(item.lemma == "hus" for item in result.items)


def test_search_returns_no_did_you_mean_when_direct_match(tmp_path):
    db = _db_path(tmp_path)
    _add_word_directly(db, "hus")
    cor_local = FakeCORLocalLexiconService()
    use_case = WordbankUseCase(db, cor_local_lexicon_service=cor_local)

    result = use_case.search_lemmas("hus")

    assert result.did_you_mean is None
    assert any(item.lemma == "hus" for item in result.items)


def test_search_returns_no_did_you_mean_when_no_correction_found(tmp_path):
    db = _db_path(tmp_path)
    _add_word_directly(db, "hus")
    cor_local = FakeCORLocalLexiconService()
    use_case = WordbankUseCase(db, cor_local_lexicon_service=cor_local)

    # "xyz" has no close wordbank lemma
    result = use_case.search_lemmas("xyz")

    assert result.did_you_mean is None
    assert result.items == []


def test_cor_search_returns_did_you_mean_when_typo(tmp_path):
    db = _db_path(tmp_path)
    hus_entry = _cor_local_entry(
        cor_id="COR.HUS.LEM",
        lemma="hus",
        gloss="house",
        form="hus",
        lemma_idx=1,
        pos_tag="NOUN",
        morphology="Gender=Neut|Number=Sing|Definite=Ind",
        gram_raw="sb.itk.sg.ubest",
    )
    cor_local = FakeCORLocalLexiconService(
        by_form={"hus": [hus_entry]},
        unique_lemmas=frozenset(["hus"]),
    )
    use_case = WordbankUseCase(db, cor_local_lexicon_service=cor_local)

    result = use_case.search_cor_form("huse", include_translations=False)

    assert result.did_you_mean == "hus"
    assert len(result.groups) > 0
    assert result.groups[0].lemma == "hus"


def test_cor_search_no_did_you_mean_when_direct_match(tmp_path):
    db = _db_path(tmp_path)
    hus_entry = _cor_local_entry(
        cor_id="COR.HUS.LEM",
        lemma="hus",
        gloss="house",
        form="hus",
        lemma_idx=1,
        pos_tag="NOUN",
        morphology="Gender=Neut|Number=Sing|Definite=Ind",
        gram_raw="sb.itk.sg.ubest",
    )
    cor_local = FakeCORLocalLexiconService(
        by_form={"hus": [hus_entry]},
        unique_lemmas=frozenset(["hus"]),
    )
    use_case = WordbankUseCase(db, cor_local_lexicon_service=cor_local)

    result = use_case.search_cor_form("hus", include_translations=False)

    assert result.did_you_mean is None
    assert len(result.groups) > 0
