from __future__ import annotations

from pathlib import Path

import pytest

from app.services.cor_local import CORLocalEntry
from app.services.use_cases.wordbank import WordbankUseCase
from tests.helpers.factories import _db_path
from tests.helpers.fakes import (
    FakeCORLocalLexiconService,
    FakeGeminiWordTranslationService,
    FakeTranslationService,
)

def test_wordbank_search_cor_form_prefers_azure_for_non_gloss_lemma_translations(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(
        by_form={
            "bogen": [
                CORLocalEntry(
                    cor_id="COR.123.111.01",
                    lemma="bog",
                    gloss=None,
                    gram_raw="sb.fk.sg.best",
                    form="bogen",
                    norm="N",
                    lemma_idx=123,
                    gram_code=111,
                    variation=1,
                    pos_tag="NOUN",
                    morphology="Gender=Com|Number=Sing|Definite=Def",
                    features={"Gender": "Com", "Number": "Sing", "Definite": "Def"},
                    extra_tags=[],
                ),
            ]
        }
    )
    gemini_translation = FakeGeminiWordTranslationService({})
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=local_cor,
        translation_service=FakeTranslationService({"en bog": "a book"}),
        gemini_word_translation_service=gemini_translation,
    )

    response = use_case.search_cor_form("bogen", limit=100)

    assert response.groups[0].variants[0].lemma_translation == "book"
    assert response.groups[0].variants[0].gloss_translation is None
    assert gemini_translation.batch_calls == []
    assert gemini_translation.calls == []

def test_wordbank_search_cor_form_uses_gemini_for_glossed_lemma_translations(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(
        by_form={
            "bogen": [
                CORLocalEntry(
                    cor_id="COR.123.111.01",
                    lemma="bog",
                    gloss="book",
                    gram_raw="sb.fk.sg.best",
                    form="bogen",
                    norm="N",
                    lemma_idx=123,
                    gram_code=111,
                    variation=1,
                    pos_tag="NOUN",
                    morphology="Gender=Com|Number=Sing|Definite=Def",
                    features={"Gender": "Com", "Number": "Sing", "Definite": "Def"},
                    extra_tags=[],
                ),
            ]
        }
    )
    gemini_translation = FakeGeminiWordTranslationService({("bogen", "bog", "book"): "book"})
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=local_cor,
        translation_service=FakeTranslationService({"book": "book"}),
        gemini_word_translation_service=gemini_translation,
    )

    response = use_case.search_cor_form("bogen", limit=100)

    assert response.groups[0].variants[0].lemma_translation == "book"
    assert response.groups[0].variants[0].gloss_translation == "book"
    assert gemini_translation.batch_calls == [[("bogen", "bog", "book")]]
    assert gemini_translation.calls == []

def test_wordbank_search_cor_form_keeps_noun_articles_when_provider_returns_them(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(
        by_form={
            "bogen": [
                CORLocalEntry(
                    cor_id="COR.123.111.01",
                    lemma="bog",
                    gloss="book",
                    gram_raw="sb.fk.sg.best",
                    form="bogen",
                    norm="N",
                    lemma_idx=123,
                    gram_code=111,
                    variation=1,
                    pos_tag="NOUN",
                    morphology="Gender=Com|Number=Sing|Definite=Def",
                    features={"Gender": "Com", "Number": "Sing", "Definite": "Def"},
                    extra_tags=[],
                ),
            ]
        }
    )
    gemini_translation = FakeGeminiWordTranslationService({("bogen", "bog", "book"): "the book"})
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=local_cor,
        translation_service=FakeTranslationService({"bog": "book", "book": "book"}),
        gemini_word_translation_service=gemini_translation,
    )

    response = use_case.search_cor_form("bogen", limit=100)

    assert response.groups[0].variants[0].lemma_translation == "the book"
    assert response.groups[0].variants[0].gloss_translation == "book"

def test_wordbank_search_cor_form_does_not_retry_missing_batch_items_with_single_calls(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(
        by_form={
            "bogen": [
                CORLocalEntry(
                    cor_id="COR.123.111.01",
                    lemma="bog",
                    gloss="book",
                    gram_raw="sb.fk.sg.best",
                    form="bogen",
                    norm="N",
                    lemma_idx=123,
                    gram_code=111,
                    variation=1,
                    pos_tag="NOUN",
                    morphology="Gender=Com|Number=Sing|Definite=Def",
                    features={"Gender": "Com", "Number": "Sing", "Definite": "Def"},
                    extra_tags=[],
                ),
            ]
        }
    )
    gemini_translation = FakeGeminiWordTranslationService(
        {("bogen", "bog", "book"): "book"},
        batch_overrides={("bogen", "bog", "book"): None},
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=local_cor,
        translation_service=FakeTranslationService({"book": "book"}),
        gemini_word_translation_service=gemini_translation,
    )

    response = use_case.search_cor_form("bogen", limit=100)

    assert response.groups[0].variants[0].lemma_translation is None
    assert response.groups[0].variants[0].gloss_translation == "book"
    assert gemini_translation.batch_calls == [[("bogen", "bog", "book")]]
    assert gemini_translation.calls == []

def test_wordbank_search_cor_form_uses_gemini_when_azure_echoes_lemma(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(
        by_form={
            "bogen": [
                CORLocalEntry(
                    cor_id="COR.123.111.01",
                    lemma="bog",
                    gloss=None,
                    gram_raw="sb.fk.sg.best",
                    form="bogen",
                    norm="N",
                    lemma_idx=123,
                    gram_code=111,
                    variation=1,
                    pos_tag="NOUN",
                    morphology="Gender=Com|Number=Sing|Definite=Def",
                    features={"Gender": "Com", "Number": "Sing", "Definite": "Def"},
                    extra_tags=[],
                ),
            ]
        }
    )
    gemini_translation = FakeGeminiWordTranslationService({("bogen", "bog", None): "book"})
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=local_cor,
        translation_service=FakeTranslationService({"en bog": "en bog"}),
        gemini_word_translation_service=gemini_translation,
    )

    response = use_case.search_cor_form("bogen", limit=100)

    assert response.groups[0].variants[0].lemma_translation == "book"
    assert response.groups[0].variants[0].gloss_translation is None
    assert gemini_translation.batch_calls == [[("bogen", "bog", None)]]
    assert gemini_translation.calls == []

def test_wordbank_search_cor_form_raises_when_azure_is_unavailable(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(
        by_form={
            "bogen": [
                CORLocalEntry(
                    cor_id="COR.123.111.01",
                    lemma="bog",
                    gloss="book",
                    gram_raw="sb.fk.sg.best",
                    form="bogen",
                    norm="N",
                    lemma_idx=123,
                    gram_code=111,
                    variation=1,
                    pos_tag="NOUN",
                    morphology="Gender=Com|Number=Sing|Definite=Def",
                    features={"Gender": "Com", "Number": "Sing", "Definite": "Def"},
                    extra_tags=[],
                ),
            ]
        }
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=local_cor,
        translation_service=None,
        gemini_word_translation_service=FakeGeminiWordTranslationService({("bogen", "bog", "book"): "the book"}),
    )

    with pytest.raises(RuntimeError, match="Azure translation is unavailable"):
        use_case.search_cor_form("bogen", limit=100)
