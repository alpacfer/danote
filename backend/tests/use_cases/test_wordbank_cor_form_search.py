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


def test_wordbank_search_cor_form_groups_variants_by_lemma_gloss_pos(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(
        by_form={
            "lærer": [
                CORLocalEntry(
                    cor_id="COR.49032.110.01",
                    lemma="lærer",
                    gloss="teacher",
                    gram_raw="sb.fk.sg.ubest",
                    form="lærer",
                    norm="N",
                    lemma_idx=49032,
                    gram_code=110,
                    variation=1,
                    pos_tag="NOUN",
                    morphology="Gender=Com|Number=Sing|Definite=Ind",
                    features={"Gender": "Com", "Number": "Sing", "Definite": "Ind"},
                    extra_tags=[],
                ),
                CORLocalEntry(
                    cor_id="COR.49032.112.01",
                    lemma="lærer",
                    gloss="teacher",
                    gram_raw="sb.fk.pl.ubest",
                    form="lærere",
                    norm="N",
                    lemma_idx=49032,
                    gram_code=112,
                    variation=1,
                    pos_tag="NOUN",
                    morphology="Gender=Com|Number=Plur|Definite=Ind",
                    features={"Gender": "Com", "Number": "Plur", "Definite": "Ind"},
                    extra_tags=[],
                ),
                CORLocalEntry(
                    cor_id="COR.30686.203.01",
                    lemma="lære",
                    gloss="learn",
                    gram_raw="vb.præs.akt",
                    form="lærer",
                    norm="N",
                    lemma_idx=30686,
                    gram_code=203,
                    variation=1,
                    pos_tag="VERB",
                    morphology="Tense=Pres|VerbForm=Fin|Voice=Act",
                    features={"Tense": "Pres", "VerbForm": "Fin", "Voice": "Act"},
                    extra_tags=[],
                ),
            ]
        }
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=local_cor,
        translation_service=FakeTranslationService(
            {
                "en lærer": "a teacher",
                "at lære": "learn",
            }
        ),
    )

    response = use_case.search_cor_form("LÆRER", limit=100)

    assert response.form == "lærer"
    assert len(response.groups) == 2
    assert response.groups[0].lemma == "lærer"
    assert response.groups[0].gloss == "teacher"
    assert response.groups[0].pos_tag == "NOUN"
    assert [variant.cor_id for variant in response.groups[0].variants] == [
        "COR.49032.110.01",
        "COR.49032.112.01",
    ]
    assert response.groups[0].variants[0].lemma_translation == "teacher"
    assert response.groups[0].variants[1].lemma_translation == "teacher"
    assert response.groups[1].lemma == "lære"
    assert response.groups[1].pos_tag == "VERB"
    assert response.groups[1].variants[0].lemma_translation == "to learn"

def test_wordbank_search_cor_form_uses_frame_identity_for_homograph_lemma_translations(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(
        by_form={
            "lærer": [
                CORLocalEntry(
                    cor_id="COR.100.203.01",
                    lemma="lære",
                    gloss=None,
                    gram_raw="vb.præs.akt",
                    form="lærer",
                    norm="N",
                    lemma_idx=100,
                    gram_code=203,
                    variation=1,
                    pos_tag="VERB",
                    morphology="Tense=Pres|VerbForm=Fin|Voice=Act",
                    features={"Tense": "Pres", "VerbForm": "Fin", "Voice": "Act"},
                    extra_tags=[],
                ),
                CORLocalEntry(
                    cor_id="COR.200.110.01",
                    lemma="lære",
                    gloss=None,
                    gram_raw="sb.fk.sg.ubest",
                    form="lærer",
                    norm="N",
                    lemma_idx=200,
                    gram_code=110,
                    variation=1,
                    pos_tag="NOUN",
                    morphology="Gender=Com|Number=Sing|Definite=Ind",
                    features={"Gender": "Com", "Number": "Sing", "Definite": "Ind"},
                    extra_tags=[],
                ),
            ]
        }
    )
    translation_service = FakeTranslationService(
        {
            "at lære": "learn",
            "en lære": "a doctrine",
        }
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=local_cor,
        translation_service=translation_service,
    )

    response = use_case.search_cor_form("lærer", limit=100)
    by_pos = {group.pos_tag: group.variants[0].lemma_translation for group in response.groups}

    assert by_pos["VERB"] == "to learn"
    assert by_pos["NOUN"] == "doctrine"
    assert "at lære" in translation_service.calls
    assert "en lære" in translation_service.calls

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

def test_wordbank_search_cor_form_forces_verb_gemini_results_to_infinitive(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(
        by_form={
            "morer": [
                CORLocalEntry(
                    cor_id="COR.777.203.01",
                    lemma="more",
                    gloss="amuse",
                    gram_raw="vb.præs.akt",
                    form="morer",
                    norm="N",
                    lemma_idx=777,
                    gram_code=203,
                    variation=1,
                    pos_tag="VERB",
                    morphology="Tense=Pres|VerbForm=Fin|Voice=Act",
                    features={"Tense": "Pres", "VerbForm": "Fin", "Voice": "Act"},
                    extra_tags=[],
                ),
            ]
        }
    )
    gemini_translation = FakeGeminiWordTranslationService({("morer", "more", "amuse"): "amuse"})
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=local_cor,
        translation_service=FakeTranslationService({"at more": "more", "amuse": "amuse"}),
        gemini_word_translation_service=gemini_translation,
    )

    response = use_case.search_cor_form("morer", limit=100)

    assert response.groups[0].variants[0].lemma_translation == "to amuse"
    assert response.groups[0].variants[0].gloss_translation == "amuse"

def test_wordbank_search_cor_form_uses_gemini_when_azure_echoes_verb_frame(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(
        by_form={
            "morer": [
                CORLocalEntry(
                    cor_id="COR.777.203.01",
                    lemma="more",
                    gloss="amuse",
                    gram_raw="vb.præs.akt",
                    form="morer",
                    norm="N",
                    lemma_idx=777,
                    gram_code=203,
                    variation=1,
                    pos_tag="VERB",
                    morphology="Tense=Pres|VerbForm=Fin|Voice=Act",
                    features={"Tense": "Pres", "VerbForm": "Fin", "Voice": "Act"},
                    extra_tags=[],
                ),
            ]
        }
    )
    gemini_translation = FakeGeminiWordTranslationService({("morer", "more", "amuse"): "amuse"})
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=local_cor,
        translation_service=FakeTranslationService({"at more": "at more", "amuse": "amuse"}),
        gemini_word_translation_service=gemini_translation,
    )

    response = use_case.search_cor_form("morer", limit=100)

    assert response.groups[0].variants[0].lemma_translation == "to amuse"
    assert gemini_translation.batch_calls == [[("morer", "more", "amuse")]]

def test_wordbank_search_cor_form_uses_gemini_when_azure_returns_literal_verb_infinitive(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(
        by_form={
            "mor": [
                CORLocalEntry(
                    cor_id="COR.35834.209.01",
                    lemma="more",
                    gloss=None,
                    gram_raw="vb.imp",
                    form="mor",
                    norm="N",
                    lemma_idx=35834,
                    gram_code=209,
                    variation=1,
                    pos_tag="VERB",
                    morphology="Mood=Imp|VerbForm=Fin",
                    features={"Mood": "Imp", "VerbForm": "Fin"},
                    extra_tags=[],
                ),
            ]
        }
    )
    gemini_translation = FakeGeminiWordTranslationService({("mor", "more", None): "amuse"})
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=local_cor,
        translation_service=FakeTranslationService({"at more": "to more"}),
        gemini_word_translation_service=gemini_translation,
    )

    response = use_case.search_cor_form("mor", limit=100)

    assert response.groups[0].variants[0].lemma_translation == "to amuse"
    assert gemini_translation.batch_calls == [[("mor", "more", None)]]

def test_wordbank_search_cor_form_strips_function_word_prefix_from_noun_frame_translation(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(
        by_form={
            "vad": [
                CORLocalEntry(
                    cor_id="COR.39436.209.01",
                    lemma="vade",
                    gloss=None,
                    gram_raw="vb.imp",
                    form="vad",
                    norm="N",
                    lemma_idx=39436,
                    gram_code=209,
                    variation=1,
                    pos_tag="VERB",
                    morphology="Mood=Imp|VerbForm=Fin",
                    features={"Mood": "Imp", "VerbForm": "Fin"},
                    extra_tags=[],
                ),
                CORLocalEntry(
                    cor_id="COR.75509.120.01",
                    lemma="vad",
                    gloss=None,
                    gram_raw="sb.itk.sg.ubest",
                    form="vad",
                    norm="N",
                    lemma_idx=75509,
                    gram_code=120,
                    variation=1,
                    pos_tag="NOUN",
                    morphology="Gender=Neut|Number=Sing|Definite=Ind",
                    features={"Gender": "Neut", "Number": "Sing", "Definite": "Ind"},
                    extra_tags=[],
                ),
            ]
        }
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=local_cor,
        translation_service=FakeTranslationService({"at vade": "to wade", "et vad": "and bet"}),
        gemini_word_translation_service=None,
    )

    response = use_case.search_cor_form("vad", limit=100)

    by_pos = {group.pos_tag: group.variants[0] for group in response.groups}
    assert by_pos["VERB"].lemma_translation == "to wade"
    assert by_pos["NOUN"].lemma_translation == "bet"

def test_wordbank_search_cor_form_normalizes_verb_frame_artifacts_from_translation(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(
        by_form={
            "vandet": [
                CORLocalEntry(
                    cor_id="COR.36401.208.01",
                    lemma="vande",
                    gloss=None,
                    gram_raw="vb.perf.part",
                    form="vandet",
                    norm="N",
                    lemma_idx=36401,
                    gram_code=208,
                    variation=1,
                    pos_tag="VERB",
                    morphology="Aspect=Perf|VerbForm=Part",
                    features={"Aspect": "Perf", "VerbForm": "Part"},
                    extra_tags=[],
                ),
            ]
        }
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=local_cor,
        translation_service=FakeTranslationService({"at vande": "that the water"}),
        gemini_word_translation_service=None,
    )

    response = use_case.search_cor_form("vandet", limit=100)

    assert response.groups[0].variants[0].lemma_translation == "to water"

def test_wordbank_search_cor_form_prefers_gloss_hint_when_gemini_echoes_noun_lemma(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(
        by_form={
            "mor": [
                CORLocalEntry(
                    cor_id="COR.51046.110.01",
                    lemma="mor",
                    gloss="jordlag",
                    gram_raw="sb.fk.sg.ubest",
                    form="mor",
                    norm="N",
                    lemma_idx=51046,
                    gram_code=110,
                    variation=1,
                    pos_tag="NOUN",
                    morphology="Gender=Com|Number=Sing|Definite=Ind",
                    features={"Gender": "Com", "Number": "Sing", "Definite": "Ind"},
                    extra_tags=[],
                ),
            ]
        }
    )
    gemini_translation = FakeGeminiWordTranslationService({("mor", "mor", "jordlag"): "mor"})
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=local_cor,
        translation_service=FakeTranslationService({"en mor": "a mother", "jordlag": "soil layer"}),
        gemini_word_translation_service=gemini_translation,
    )

    response = use_case.search_cor_form("mor", limit=100)

    assert response.groups[0].variants[0].lemma_translation == "soil layer"
    assert response.groups[0].variants[0].gloss_translation == "soil layer"
    assert gemini_translation.batch_calls == [[("mor", "mor", "jordlag")]]

def test_wordbank_search_cor_form_translates_comma_separated_gloss_parts(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(
        by_form={
            "glas": [
                CORLocalEntry(
                    cor_id="COR.50306.120.01",
                    lemma="glas",
                    gloss="drikkeglas, brilleglas",
                    gram_raw="sb.itk.sg.ubest",
                    form="glas",
                    norm="N",
                    lemma_idx=50306,
                    gram_code=120,
                    variation=1,
                    pos_tag="NOUN",
                    morphology="Gender=Neut|Number=Sing|Definite=Ind",
                    features={"Gender": "Neut", "Number": "Sing", "Definite": "Ind"},
                    extra_tags=[],
                ),
            ]
        }
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=local_cor,
        translation_service=FakeTranslationService(
            {
                "et glas": "a glass",
                "drikkeglas": "drinking glass",
                "brilleglas": "eyeglass lens",
            }
        ),
    )

    response = use_case.search_cor_form("glas", limit=100)

    assert response.groups[0].variants[0].gloss_translation == "drinking glass, eyeglass lens"

def test_wordbank_search_cor_form_consolidates_same_entry_with_multiple_grams(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(
        by_form={
            "glas": [
                CORLocalEntry(
                    cor_id="COR.50306.120.01",
                    lemma="glas",
                    gloss="drikkeglas, brilleglas",
                    gram_raw="sb.itk.sg.ubest",
                    form="glas",
                    norm="N",
                    lemma_idx=50306,
                    gram_code=120,
                    variation=1,
                    pos_tag="NOUN",
                    morphology="Gender=Neut|Number=Sing|Definite=Ind",
                    features={"Gender": "Neut", "Number": "Sing", "Definite": "Ind"},
                    extra_tags=[],
                ),
                CORLocalEntry(
                    cor_id="COR.50306.122.01",
                    lemma="glas",
                    gloss="drikkeglas, brilleglas",
                    gram_raw="sb.itk.pl.ubest",
                    form="glas",
                    norm="N",
                    lemma_idx=50306,
                    gram_code=122,
                    variation=1,
                    pos_tag="NOUN",
                    morphology="Gender=Neut|Number=Plur|Definite=Ind",
                    features={"Gender": "Neut", "Number": "Plur", "Definite": "Ind"},
                    extra_tags=[],
                ),
            ]
        }
    )
    use_case = WordbankUseCase(_db_path(tmp_path), cor_local_lexicon_service=local_cor)

    response = use_case.search_cor_form("glas", limit=100, include_translations=False)

    assert len(response.groups) == 1
    assert len(response.groups[0].variants) == 1
    assert response.groups[0].variants[0].gram_raw == "sb.itk.sg.ubest | sb.itk.pl.ubest"

def test_wordbank_search_cor_form_prefers_glossed_entries_within_same_pos(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(
        by_form={
            "glas": [
                CORLocalEntry(
                    cor_id="COR.50306.120.01",
                    lemma="glas",
                    gloss="drikkeglas, brilleglas",
                    gram_raw="sb.itk.sg.ubest",
                    form="glas",
                    norm="N",
                    lemma_idx=50306,
                    gram_code=120,
                    variation=1,
                    pos_tag="NOUN",
                    morphology="Gender=Neut|Number=Sing|Definite=Ind",
                    features={"Gender": "Neut", "Number": "Sing", "Definite": "Ind"},
                    extra_tags=[],
                ),
                CORLocalEntry(
                    cor_id="COR.46180.120.01",
                    lemma="glas",
                    gloss=None,
                    gram_raw="sb.itk.sg.ubest",
                    form="glas",
                    norm="N",
                    lemma_idx=46180,
                    gram_code=120,
                    variation=1,
                    pos_tag="NOUN",
                    morphology="Gender=Neut|Number=Sing|Definite=Ind",
                    features={"Gender": "Neut", "Number": "Sing", "Definite": "Ind"},
                    extra_tags=[],
                ),
            ]
        }
    )
    use_case = WordbankUseCase(_db_path(tmp_path), cor_local_lexicon_service=local_cor)

    response = use_case.search_cor_form("glas", limit=100, include_translations=False)

    assert len(response.groups) == 1
    assert len(response.groups[0].variants) == 1
    assert response.groups[0].variants[0].gloss == "drikkeglas, brilleglas"

def test_wordbank_search_cor_lemma_paradigm_returns_all_forms(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(
        by_lemma_idx={
            49032: [
                CORLocalEntry(
                    cor_id="COR.49032.110.01",
                    lemma="lærer",
                    gloss="teacher",
                    gram_raw="sb.fk.sg.ubest",
                    form="lærer",
                    norm="N",
                    lemma_idx=49032,
                    gram_code=110,
                    variation=1,
                    pos_tag="NOUN",
                    morphology="Gender=Com|Number=Sing|Definite=Ind",
                    features={"Gender": "Com", "Number": "Sing", "Definite": "Ind"},
                    extra_tags=[],
                ),
                CORLocalEntry(
                    cor_id="COR.49032.112.01",
                    lemma="lærer",
                    gloss="teacher",
                    gram_raw="sb.fk.pl.ubest",
                    form="lærere",
                    norm="N",
                    lemma_idx=49032,
                    gram_code=112,
                    variation=1,
                    pos_tag="NOUN",
                    morphology="Gender=Com|Number=Plur|Definite=Ind",
                    features={"Gender": "Com", "Number": "Plur", "Definite": "Ind"},
                    extra_tags=[],
                ),
            ]
        }
    )
    use_case = WordbankUseCase(_db_path(tmp_path), cor_local_lexicon_service=local_cor)

    response = use_case.search_cor_lemma_paradigm(49032, limit=1000)

    assert response.lemma_idx == 49032
    assert [variant.form for variant in response.variants] == ["lærer", "lærere"]

