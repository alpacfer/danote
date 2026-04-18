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


def test_wordbank_search_cor_form_uses_gemini_for_self_translated_bile(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(
        by_form={
            "bil": [
                CORLocalEntry(
                    cor_id="COR.36439.209.01",
                    lemma="bile",
                    gloss="køre i bil",
                    gram_raw="vb.imp",
                    form="bil",
                    norm="N",
                    lemma_idx=36439,
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
    gemini_translation = FakeGeminiWordTranslationService({("bil", "bile", "køre i bil"): "drive"})
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=local_cor,
        translation_service=FakeTranslationService(
            {"at bile": "to bile", "køre i bil": "go by car"},
            provider="deepl_translator",
        ),
        gemini_word_translation_service=gemini_translation,
    )

    response = use_case.search_cor_form("bil", limit=100)

    variant = response.groups[0].variants[0]
    assert variant.lemma_translation == "to drive"
    assert variant.saveable_translation == "to drive"
    assert variant.gloss_translation == "go by car"
    assert variant.lemma_translation_provider == "gemini_word_translation"
    assert variant.lemma_translation_status == "gemini"
    assert variant.lemma_translation_reason == "gemini_ok"
    assert gemini_translation.batch_calls == [[("bil", "bile", "køre i bil")]]


def test_wordbank_search_cor_form_uses_gemini_for_glossless_self_translated_bile(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(
        by_form={
            "bil": [
                CORLocalEntry(
                    cor_id="COR.36439.209.01",
                    lemma="bile",
                    gloss=None,
                    gram_raw="vb.imp",
                    form="bil",
                    norm="N",
                    lemma_idx=36439,
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
    gemini_translation = FakeGeminiWordTranslationService({("bil", "bile", None): "drive"})
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=local_cor,
        translation_service=FakeTranslationService(
            {"at bile": "to bile"},
            provider="deepl_translator",
        ),
        gemini_word_translation_service=gemini_translation,
    )

    response = use_case.search_cor_form("bil", limit=100)

    variant = response.groups[0].variants[0]
    assert variant.lemma_translation == "to drive"
    assert variant.saveable_translation == "to drive"
    assert variant.gloss_translation is None
    assert variant.lemma_translation_provider == "gemini_word_translation"
    assert variant.lemma_translation_status == "gemini"
    assert variant.lemma_translation_reason == "gemini_ok"
    assert gemini_translation.batch_calls == [[("bil", "bile", None)]]


def test_wordbank_search_cor_form_keeps_glossless_have_when_provider_returns_valid_english_verb(
    tmp_path: Path,
) -> None:
    local_cor = FakeCORLocalLexiconService(
        by_form={
            "har": [
                CORLocalEntry(
                    cor_id="COR.30035.203.01",
                    lemma="have",
                    gloss=None,
                    gram_raw="vb.præs.akt",
                    form="har",
                    norm="N",
                    lemma_idx=30035,
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
            {"at have": "to have"},
            provider="deepl_translator",
        ),
    )

    response = use_case.search_cor_form("har", limit=100)

    variant = response.groups[0].variants[0]
    assert variant.lemma_translation == "to have"
    assert variant.saveable_translation == "to have"
    assert variant.lemma_translation_provider == "deepl_translator"
    assert variant.lemma_translation_status == "provider"
    assert variant.lemma_translation_reason == "provider_ok"


def test_wordbank_search_cor_form_hides_self_translated_bile_when_gemini_has_no_better_result(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(
        by_form={
            "bil": [
                CORLocalEntry(
                    cor_id="COR.36439.209.01",
                    lemma="bile",
                    gloss="køre i bil",
                    gram_raw="vb.imp",
                    form="bil",
                    norm="N",
                    lemma_idx=36439,
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
    gemini_translation = FakeGeminiWordTranslationService(
        {("bil", "bile", "køre i bil"): None},
        batch_overrides={("bil", "bile", "køre i bil"): None},
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=local_cor,
        translation_service=FakeTranslationService(
            {"at bile": "to bile", "køre i bil": "go by car"},
            provider="deepl_translator",
        ),
        gemini_word_translation_service=gemini_translation,
    )

    response = use_case.search_cor_form("bil", limit=100)

    variant = response.groups[0].variants[0]
    assert variant.lemma_translation is None
    assert variant.saveable_translation == "go by car"
    assert variant.gloss_translation == "go by car"
    assert variant.lemma_translation_provider == "deepl_translator"
    assert variant.lemma_translation_status == "gloss_fallback"
    assert variant.lemma_translation_reason == "gloss_fallback_used"
    assert gemini_translation.batch_calls == [[("bil", "bile", "køre i bil")]]


def test_wordbank_search_cor_form_keeps_self_translated_bile_when_gemini_echoes_too(tmp_path: Path) -> None:
    local_cor = FakeCORLocalLexiconService(
        by_form={
            "bil": [
                CORLocalEntry(
                    cor_id="COR.36439.209.01",
                    lemma="bile",
                    gloss="køre i bil",
                    gram_raw="vb.imp",
                    form="bil",
                    norm="N",
                    lemma_idx=36439,
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
    gemini_translation = FakeGeminiWordTranslationService(
        {("bil", "bile", "køre i bil"): "bile"},
        batch_overrides={("bil", "bile", "køre i bil"): "bile"},
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=local_cor,
        translation_service=FakeTranslationService(
            {"at bile": "to bile", "køre i bil": "go by car"},
            provider="deepl_translator",
        ),
        gemini_word_translation_service=gemini_translation,
    )

    response = use_case.search_cor_form("bil", limit=100)

    variant = response.groups[0].variants[0]
    assert variant.lemma_translation == "to bile"
    assert variant.saveable_translation == "to bile"
    assert variant.gloss_translation == "go by car"
    assert variant.lemma_translation_provider == "gemini_word_translation"
    assert variant.lemma_translation_status == "gemini"
    assert variant.lemma_translation_reason == "gemini_ok"
    assert gemini_translation.batch_calls == [[("bil", "bile", "køre i bil")]]


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

def test_wordbank_search_cor_form_trusts_gemini_when_it_echoes_noun_lemma(tmp_path: Path) -> None:
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

    assert response.groups[0].variants[0].lemma_translation == "mor"
    assert response.groups[0].variants[0].saveable_translation == "mor"
    assert response.groups[0].variants[0].gloss_translation == "soil layer"
    assert response.groups[0].variants[0].lemma_translation_provider == "gemini_word_translation"
    assert response.groups[0].variants[0].lemma_translation_status == "gemini"
    assert response.groups[0].variants[0].lemma_translation_reason == "gemini_ok"
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
