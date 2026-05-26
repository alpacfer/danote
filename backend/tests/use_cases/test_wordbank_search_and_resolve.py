from __future__ import annotations

from pathlib import Path

from app.nlp.adapter import NLPToken
from app.services.cor import COREntry
from app.services.use_cases.analyze import AnalyzeNoteUseCase
from app.services.use_cases.wordbank import WordbankUseCase
from tests.helpers.factories import _bog_homograph_cor_local, _cor_local_entry, _db_path
from tests.helpers.fakes import (
    FakeCORLexiconService,
    FakeCORLocalLexiconService,
    FakeGeminiWordTranslationService,
    FakeTranslationService,
)


def test_wordbank_search_lemmas_matches_variations(tmp_path: Path) -> None:
    use_case = WordbankUseCase(_db_path(tmp_path))
    use_case.add_word("Bogens", "bog")
    use_case.add_word("Huse", "hus")

    result = use_case.search_lemmas("gens")

    assert len(result.items) == 1
    assert result.items[0].lemma == "bog"
    assert result.items[0].match_surface == "bogens"


def test_wordbank_search_lemmas_respects_language_mode_for_saved_translations(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({"kat": "cat"}),
    )
    use_case.add_word("Kat", "kat")

    danish_result = use_case.search_lemmas("cat", language="da")
    english_result = use_case.search_lemmas("cat", language="en")

    assert danish_result.items == []
    assert english_result.items[0].lemma == "kat"
    assert english_result.items[0].matched_via == "english_translation"


def test_wordbank_search_lemmas_uses_language_specific_typo_candidates(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({"kat": "cat"}),
    )
    use_case.add_word("Kat", "kat")

    danish_result = use_case.search_lemmas("cta", language="da")
    english_result = use_case.search_lemmas("cta", language="en")

    assert danish_result.did_you_mean is None
    assert english_result.did_you_mean == "cat"
    assert english_result.items[0].lemma == "kat"


def test_wordbank_resolve_query_uses_static_danish_pronoun_without_providers(tmp_path: Path) -> None:
    translation_service = FakeTranslationService({"du": "provider should not be used"})
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        translation_service=translation_service,
        cor_local_lexicon_service=FakeCORLocalLexiconService(),
    )

    resolved = use_case.resolve_query("Du")

    assert translation_service.calls == []
    assert resolved.classification == "known"
    assert resolved.query_surface == "du"
    assert resolved.resolved_lemma == "du"
    assert resolved.da_to_en_translation == "you"
    assert resolved.query_pos_tag == "PRON"
    assert resolved.query_morphology == "PronType=Prs|Case=Nom|Person=2|Number=Sing"
    assert resolved.word_actions[0].action_type == "open_wordbank"
    assert resolved.word_actions[0].lemma == "du"
    assert resolved.word_actions[0].translation_label == "you"


def test_wordbank_resolve_query_uses_static_english_pronoun_without_providers(tmp_path: Path) -> None:
    translation_service = FakeTranslationService({"you": "provider should not be used"}, detected_languages={"you": "EN"})
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        translation_service=translation_service,
        cor_local_lexicon_service=FakeCORLocalLexiconService(),
    )

    resolved = use_case.resolve_query("you")

    assert translation_service.calls == []
    assert resolved.classification == "known"
    assert resolved.query_language == "en"
    assert resolved.en_to_da_translation == "du"
    assert resolved.resolved_lemma == "du"
    assert resolved.en_to_da_morphology == "PronType=Prs|Case=Nom|Person=2|Number=Sing"
    assert resolved.word_actions[0].action_type == "open_wordbank"
    assert resolved.word_actions[0].surface == "du"


def test_wordbank_resolve_query_uses_static_hv_word_without_providers(tmp_path: Path) -> None:
    translation_service = FakeTranslationService({"hvor": "provider should not be used"}, detected_languages={"where": "EN"})
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        translation_service=translation_service,
        cor_local_lexicon_service=FakeCORLocalLexiconService(),
    )

    danish_resolved = use_case.resolve_query("Hvor")
    english_resolved = use_case.resolve_query("where")

    assert translation_service.calls == []
    assert danish_resolved.classification == "known"
    assert danish_resolved.resolved_lemma == "hvor"
    assert danish_resolved.da_to_en_translation == "where"
    assert danish_resolved.query_pos_tag == "ADV"
    assert english_resolved.query_language == "en"
    assert english_resolved.en_to_da_translation == "hvor"
    assert english_resolved.word_actions[0].lemma == "hvor"


def test_wordbank_resolve_query_uses_static_presaved_word_without_providers(tmp_path: Path) -> None:
    translation_service = FakeTranslationService({"mandag": "provider should not be used"}, detected_languages={"monday": "EN"})
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        translation_service=translation_service,
        cor_local_lexicon_service=FakeCORLocalLexiconService(),
    )

    danish_resolved = use_case.resolve_query("mandag")
    english_resolved = use_case.resolve_query("Monday")

    assert translation_service.calls == []
    assert danish_resolved.classification == "known"
    assert danish_resolved.resolved_lemma == "mandag"
    assert danish_resolved.da_to_en_translation == "Monday"
    assert danish_resolved.query_pos_tag == "NOUN"
    assert english_resolved.query_language == "en"
    assert english_resolved.en_to_da_translation == "mandag"
    assert english_resolved.word_actions[0].lemma == "mandag"


def test_wordbank_search_lemmas_returns_static_pronouns_as_saved_defaults(tmp_path: Path) -> None:
    use_case = WordbankUseCase(_db_path(tmp_path))

    danish_result = use_case.search_lemmas("du")
    english_result = use_case.search_lemmas("you", language="en")

    assert danish_result.items[0].lemma == "du"
    assert danish_result.items[0].english_translation == "you"
    assert danish_result.items[0].pos_tag == "PRON"
    assert english_result.items[0].lemma == "du"
    assert english_result.items[0].match_surface is None


def test_wordbank_search_lemmas_returns_static_hv_words_as_saved_defaults(tmp_path: Path) -> None:
    use_case = WordbankUseCase(_db_path(tmp_path))

    danish_result = use_case.search_lemmas("hvorfor")
    english_result = use_case.search_lemmas("why", language="en")

    assert danish_result.items[0].lemma == "hvorfor"
    assert danish_result.items[0].english_translation == "why"
    assert danish_result.items[0].pos_tag == "ADV"
    assert english_result.items[0].lemma == "hvorfor"
    assert english_result.items[0].match_surface is None


def test_wordbank_search_lemmas_returns_static_presaved_words_as_saved_defaults(tmp_path: Path) -> None:
    use_case = WordbankUseCase(_db_path(tmp_path))

    danish_result = use_case.search_lemmas("mandag")
    english_result = use_case.search_lemmas("Monday", language="en")

    assert danish_result.items[0].lemma == "mandag"
    assert danish_result.items[0].english_translation == "Monday"
    assert danish_result.items[0].pos_tag == "NOUN"
    assert english_result.items[0].lemma == "mandag"
    assert english_result.items[0].match_surface is None


def test_wordbank_get_lemma_details_returns_static_pronoun_defaults(tmp_path: Path) -> None:
    use_case = WordbankUseCase(_db_path(tmp_path))

    details = use_case.get_lemma_details("du")

    assert details.lemma == "du"
    assert details.english_translation == "you"
    assert details.pos_tag == "PRON"
    assert details.surface_forms[0].form == "du"
    assert details.surface_forms[0].has_pronunciation is True


def test_wordbank_get_lemma_details_returns_static_presaved_defaults(tmp_path: Path) -> None:
    use_case = WordbankUseCase(_db_path(tmp_path))

    preposition_details = use_case.get_lemma_details("i")
    article_details = use_case.get_lemma_details("-en")
    question_details = use_case.get_lemma_details("hvis")
    formal_pronoun_details = use_case.get_lemma_details("I")

    assert preposition_details.lemma == "i"
    assert preposition_details.english_translation == "in / for"
    assert preposition_details.pos_tag == "ADP"
    assert article_details.lemma == "-en"
    assert article_details.english_translation == "the"
    assert question_details.lemma == "hvis"
    assert question_details.is_sectioned is True
    assert {section.english_translation for section in question_details.meaning_sections} == {"whose / if", "whose"}
    assert formal_pronoun_details.lemma == "i"
    assert formal_pronoun_details.pos_tag == "PRON"


def test_wordbank_get_lemma_details_sections_static_homographs(tmp_path: Path) -> None:
    use_case = WordbankUseCase(_db_path(tmp_path))

    en_details = use_case.get_lemma_details("en")
    der_details = use_case.get_lemma_details("der")

    assert en_details.is_sectioned is True
    assert [(section.pos_tag, section.english_translation) for section in en_details.meaning_sections] == [
        ("DET", "a / an"),
        ("NUM", "one"),
    ]
    # Articles are still presaved but no longer have a grouped reference page.
    assert en_details.meaning_sections[0].reference_links == []
    assert en_details.meaning_sections[1].reference_links[0].tab_id == "cardinal_numbers"
    assert [form.form for form in en_details.surface_forms] == ["en"]
    assert der_details.is_sectioned is True
    assert [(section.pos_tag, section.english_translation) for section in der_details.meaning_sections] == [
        ("ADV", "there"),
        ("PRON", "who / which"),
    ]
    assert der_details.meaning_sections[1].reference_links[0].tab_id == "relative"


def test_wordbank_get_lemma_details_sections_static_preposition_homographs(tmp_path: Path) -> None:
    use_case = WordbankUseCase(_db_path(tmp_path))

    details = use_case.get_lemma_details("for")

    assert details.is_sectioned is True
    assert [(section.pos_tag, section.english_translation) for section in details.meaning_sections] == [
        ("ADP", "for"),
        ("CCONJ", "because"),
    ]
    assert [section.reference_links[0].tab_id for section in details.meaning_sections] == [
        "prepositions",
        "conjunctions",
    ]


def test_wordbank_search_lemmas_uses_matched_surface_metadata(tmp_path: Path) -> None:
    use_case = WordbankUseCase(_db_path(tmp_path))
    use_case.add_word(
        "Ulykker",
        "ulykke",
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Plur|Definite=Ind",
    )

    result = use_case.search_lemmas("ulykker")

    assert len(result.items) == 1
    assert result.items[0].lemma == "ulykke"
    assert result.items[0].match_surface == "ulykker"
    assert result.items[0].pos_tag == "NOUN"
    assert result.items[0].morphology == "Gender=Com|Number=Plur|Definite=Ind"

def test_wordbank_search_lemmas_returns_query_cor_ids_for_exact_form_per_meaning(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=_bog_homograph_cor_local(),
        translation_service=FakeTranslationService({"book": "book", "swamp": "swamp"}),
    )
    use_case.add_word("Bogen", "bog", cor_id="COR.BOG.BOOK.DEF")
    use_case.add_word("Bogen", "bog", cor_id="COR.BOG.SWAMP.DEF")

    result = use_case.search_lemmas("bogen")

    assert [(item.meaning_key, item.query_cor_ids) for item in result.items] == [
        ("book", ["COR.BOG.BOOK.DEF"]),
        ("swamp", ["COR.BOG.SWAMP.DEF"]),
    ]

def test_wordbank_search_lemmas_returns_two_saved_rows_for_exact_homograph_lemma(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=_bog_homograph_cor_local(),
        translation_service=FakeTranslationService({"book": "book", "swamp": "swamp"}),
    )
    use_case.add_word("Bogen", "bog", cor_id="COR.BOG.BOOK.DEF")
    use_case.add_word("Bogen", "bog", cor_id="COR.BOG.SWAMP.DEF")

    result = use_case.search_lemmas("bog")

    assert [(item.meaning_key, item.match_surface, item.english_translation) for item in result.items] == [
        ("book", "bog", "book"),
        ("swamp", "bog", "swamp"),
    ]


def test_wordbank_search_lemmas_keeps_translation_separate_from_translated_gloss(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_lemma_idx={
                51046: [
                    _cor_local_entry(
                        cor_id="COR.MOR.PERSON.LEM",
                        lemma="mor",
                        gloss="person",
                        form="mor",
                        lemma_idx=51046,
                        pos_tag="NOUN",
                        morphology="Gender=Com|Number=Sing|Definite=Ind",
                        gram_raw="sb.fk.sg.ubest",
                    ),
                ],
                51047: [
                    _cor_local_entry(
                        cor_id="COR.MOR.SOIL.LEM",
                        lemma="mor",
                        gloss="jordlag",
                        form="mor",
                        lemma_idx=51047,
                        pos_tag="NOUN",
                        morphology="Gender=Com|Number=Sing|Definite=Ind",
                        gram_raw="sb.fk.sg.ubest",
                    ),
                ],
            }
        ),
        translation_service=FakeTranslationService({"person": "person", "jordlag": "soil layer"}),
    )
    use_case.add_word(
        "mor",
        "mor",
        search_seed={
            "lemma": "mor",
            "surface": "mor",
            "cor_id": "COR.MOR.PERSON.LEM",
            "cor_lemma_idx": 51046,
            "meaning_key": "person",
            "gloss": "person",
            "english_translation": "mother",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Sing|Definite=Ind",
        },
    )
    use_case.add_word(
        "mor",
        "mor",
        search_seed={
            "lemma": "mor",
            "surface": "mor",
            "cor_id": "COR.MOR.SOIL.LEM",
            "cor_lemma_idx": 51047,
            "meaning_key": "soil-layer",
            "gloss": "jordlag",
            "english_translation": "mother",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Sing|Definite=Ind",
        },
    )

    result = use_case.search_lemmas("mor")

    assert [
        (item.meaning_key, item.english_translation, item.gloss, item.gloss_translation)
        for item in result.items
    ] == [
        ("person", "mother", "person", "person"),
        ("soil-layer", "mother", "jordlag", "soil layer"),
    ]

def test_wordbank_search_lemmas_prefers_exact_surface_match_and_stable_variation_count(tmp_path: Path) -> None:
    use_case = WordbankUseCase(_db_path(tmp_path))
    use_case.add_word("abc", "lemma")
    use_case.add_word("aabc", "lemma")
    use_case.add_word("abcx", "lemma")

    result = use_case.search_lemmas("abc")

    assert len(result.items) == 1
    assert result.items[0].lemma == "lemma"
    assert result.items[0].match_surface == "abc"
    assert result.items[0].variation_count == 4

def test_wordbank_search_lemmas_prioritizes_exact_surface_match_over_prefix_lemmas(tmp_path: Path) -> None:
    use_case = WordbankUseCase(_db_path(tmp_path))
    use_case.add_word("abc", "target")
    for index in range(10):
        token = f"abcx{index}"
        use_case.add_word(token, token)

    result = use_case.search_lemmas("abc", limit=8)

    assert len(result.items) == 8
    assert result.items[0].lemma == "target"
    assert result.items[0].match_surface == "abc"

def test_wordbank_resolve_query_returns_variation_match_summary(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({"bog": "book", "bogen": "the book"}),
    )
    use_case.add_word("Bogen", "bog")

    resolved = use_case.resolve_query("Bogen")

    assert resolved.query_surface == "bogen"
    assert resolved.query_lemma == "bog"
    assert resolved.classification == "known"
    assert resolved.matched_lemma == "bog"
    assert resolved.matched_lemma_summary is not None
    assert resolved.matched_lemma_summary.lemma == "bog"
    assert resolved.matched_lemma_summary.english_translation == "book"

def test_wordbank_resolve_query_expands_new_word_actions_with_cor_pos_options(tmp_path: Path) -> None:
    cor_service = FakeCORLexiconService(
        {
            "gift": [
                COREntry(
                    cor_id="COR.1",
                    lemma="gift",
                    full_form="gift",
                    ordklasse="sb",
                    grammatical_function="sb.fk.sg.ubest",
                    glosse=None,
                    norm_status="N",
                    pos_tag="NOUN",
                    morphology="Gender=Com|Number=Sing|Definite=Ind",
                ),
                COREntry(
                    cor_id="COR.2",
                    lemma="gifte",
                    full_form="gift",
                    ordklasse="vb",
                    grammatical_function="vb.imp",
                    glosse=None,
                    norm_status="N",
                    pos_tag="VERB",
                    morphology="Mood=Imp|VerbForm=Fin",
                ),
            ]
        }
    )
    translation_service = FakeTranslationService(
        {
            "en gift": "a poison",
            "at gifte": "marry",
        }
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_lexicon_service=cor_service,
        translation_service=translation_service,
    )

    resolved = use_case.resolve_query("gift", include_language_detection=True)

    assert resolved.classification == "new"
    assert resolved.query_lemma == "gift"
    assert resolved.query_language == "da"
    assert (resolved.query_language_confidence or 0) >= 0.9
    assert len(resolved.word_actions) == 2
    assert [action.action_type for action in resolved.word_actions] == ["add_as_new", "add_as_new"]
    assert [action.pos_tag for action in resolved.word_actions] == ["NOUN", "VERB"]
    assert [action.lemma for action in resolved.word_actions] == ["gift", "gifte"]
    assert [action.translation_label for action in resolved.word_actions] == ["poison", "marry"]
    assert "en gift" in translation_service.calls
    assert "at gifte" in translation_service.calls

def test_wordbank_resolve_query_returns_single_best_option_per_pos(tmp_path: Path) -> None:
    cor_service = FakeCORLexiconService(
        {
            "lærer": [
                COREntry(
                    cor_id="COR.verb",
                    lemma="lære",
                    full_form="lærer",
                    ordklasse="vb",
                    grammatical_function="vb.prs.akt",
                    glosse=None,
                    norm_status="N",
                    pos_tag="VERB",
                    morphology="Tense=Pres|VerbForm=Fin|Voice=Act",
                ),
                COREntry(
                    cor_id="COR.noun.pl",
                    lemma="lære",
                    full_form="lærer",
                    ordklasse="sb",
                    grammatical_function="sb.fk.pl.ubest",
                    glosse=None,
                    norm_status="N",
                    pos_tag="NOUN",
                    morphology="Gender=Com|Number=Plur|Definite=Ind",
                ),
                COREntry(
                    cor_id="COR.noun.sg",
                    lemma="lærer",
                    full_form="lærer",
                    ordklasse="sb",
                    grammatical_function="sb.fk.sg.ubest",
                    glosse=None,
                    norm_status="N",
                    pos_tag="NOUN",
                    morphology="Gender=Com|Number=Sing|Definite=Ind",
                ),
            ]
        }
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_lexicon_service=cor_service,
        translation_service=FakeTranslationService(
            {
                "en lærer": "a teacher",
                "at lære": "to learn",
            }
        ),
    )

    resolved = use_case.resolve_query("lærer", include_language_detection=True)

    assert len(resolved.word_actions) == 2
    assert [action.pos_tag for action in resolved.word_actions] == ["NOUN", "VERB"]
    assert [action.lemma for action in resolved.word_actions] == ["lærer", "lære"]
    assert [action.translation_label for action in resolved.word_actions] == ["teacher", "to learn"]

def test_wordbank_resolve_query_batches_gemini_for_cor_options(tmp_path: Path) -> None:
    cor_service = FakeCORLexiconService(
        {
            "gift": [
                COREntry(
                    cor_id="COR.1",
                    lemma="gift",
                    full_form="gift",
                    ordklasse="sb",
                    grammatical_function="sb.fk.sg.ubest",
                    glosse=None,
                    norm_status="N",
                    pos_tag="NOUN",
                    morphology="Gender=Com|Number=Sing|Definite=Ind",
                ),
                COREntry(
                    cor_id="COR.2",
                    lemma="gifte",
                    full_form="gift",
                    ordklasse="vb",
                    grammatical_function="vb.imp",
                    glosse=None,
                    norm_status="N",
                    pos_tag="VERB",
                    morphology="Mood=Imp|VerbForm=Fin",
                ),
            ]
        }
    )
    gemini_translation = FakeGeminiWordTranslationService(
        {
            ("gift", "gift", None): "poison",
            ("gift", "gifte", None): "marry",
        }
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_lexicon_service=cor_service,
        translation_service=FakeTranslationService({}),
        gemini_word_translation_service=gemini_translation,
    )

    resolved = use_case.resolve_query("gift", include_language_detection=False)

    assert [action.translation_label for action in resolved.word_actions] == ["poison", "marry"]
    assert gemini_translation.batch_calls == [[("gift", "gift", None), ("gift", "gifte", None)]]
    assert gemini_translation.calls == []


def test_wordbank_resolve_query_suppresses_self_translated_cor_option_labels(tmp_path: Path) -> None:
    cor_service = FakeCORLexiconService(
        {
            "bil": [
                COREntry(
                    cor_id="COR.verb",
                    lemma="bile",
                    full_form="bil",
                    ordklasse="vb",
                    grammatical_function="vb.imp",
                    glosse=None,
                    norm_status="N",
                    pos_tag="VERB",
                    morphology="Mood=Imp|VerbForm=Fin",
                )
            ]
        }
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_lexicon_service=cor_service,
        translation_service=FakeTranslationService({"at bile": "to bile"}),
        gemini_word_translation_service=FakeGeminiWordTranslationService(
            {("bil", "bile", None): "bile"},
            batch_overrides={("bil", "bile", None): "bile"},
        ),
    )

    resolved = use_case.resolve_query("bil", include_language_detection=False)

    assert len(resolved.word_actions) == 1
    assert resolved.word_actions[0].lemma == "bile"
    assert resolved.word_actions[0].translation_label == "bil"


def test_wordbank_resolve_query_uses_gemini_for_self_translated_bile_with_gloss(tmp_path: Path) -> None:
    cor_service = FakeCORLexiconService(
        {
            "bil": [
                COREntry(
                    cor_id="COR.verb",
                    lemma="bile",
                    full_form="bil",
                    ordklasse="vb",
                    grammatical_function="vb.imp",
                    glosse="køre i bil",
                    norm_status="N",
                    pos_tag="VERB",
                    morphology="Mood=Imp|VerbForm=Fin",
                )
            ]
        }
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_lexicon_service=cor_service,
        translation_service=FakeTranslationService(
            {"at bile": "to bile", "køre i bil": "go by car"},
            provider="deepl_translator",
        ),
        gemini_word_translation_service=FakeGeminiWordTranslationService(
            {("bil", "bile", "køre i bil"): "drive"},
            batch_overrides={("bil", "bile", "køre i bil"): "drive"},
        ),
    )

    resolved = use_case.resolve_query("bil", include_language_detection=False)

    assert len(resolved.word_actions) == 1
    assert resolved.word_actions[0].lemma == "bile"
    assert resolved.word_actions[0].translation_label == "drive"


def test_wordbank_resolve_query_uses_framed_azure_for_non_verb_pos(tmp_path: Path) -> None:
    cor_service = FakeCORLexiconService(
        {
            "klar": [
                COREntry(
                    cor_id="COR.adj",
                    lemma="klar",
                    full_form="klar",
                    ordklasse="adj",
                    grammatical_function="adj.pos",
                    glosse=None,
                    norm_status="N",
                    pos_tag="ADJ",
                    morphology="Degree=Pos",
                )
            ]
        }
    )
    translation_service = FakeTranslationService({"en klar ting": "clear"})
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_lexicon_service=cor_service,
        translation_service=translation_service,
    )

    resolved = use_case.resolve_query("klar", include_language_detection=False)

    assert len(resolved.word_actions) == 1
    assert resolved.word_actions[0].lemma == "klar"
    assert resolved.word_actions[0].pos_tag == "ADJ"
    assert resolved.word_actions[0].translation_label == "clear"
    assert "en klar ting" in translation_service.calls

def test_wordbank_resolve_query_prefers_cor_metadata_over_runtime_nlp(tmp_path: Path) -> None:
    class ContradictingNLPAdapter:
        def tokenize(self, text: str) -> list[NLPToken]:
            return [
                NLPToken(
                    text=text,
                    lemma=text.lower(),
                    pos="NOUN",
                    morphology="Gender=Neut|Number=Sing",
                    is_punctuation=False,
                )
            ]

        def lemma_candidates_for_token(self, token: str) -> list[str]:
            return [token.lower()]

        def lemma_for_token(self, token: str) -> str | None:
            return token.lower()

        def metadata(self) -> dict[str, str]:
            return {"adapter": "contradicting"}

    cor_service = FakeCORLexiconService(
        {
            "løb": [
                COREntry(
                    cor_id="COR.3",
                    lemma="løbe",
                    full_form="løb",
                    ordklasse="vb",
                    grammatical_function="vb.præt.akt",
                    glosse=None,
                    norm_status="N",
                    pos_tag="VERB",
                    morphology="Tense=Past|VerbForm=Fin|Voice=Act",
                )
            ]
        }
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        nlp_adapter=ContradictingNLPAdapter(),
        cor_lexicon_service=cor_service,
    )

    resolved = use_case.resolve_query("løb", include_translations=False, include_language_detection=False)

    assert resolved.query_pos_tag == "VERB"
    assert resolved.query_morphology == "Tense=Past|VerbForm=Fin|Voice=Act"

def test_wordbank_resolve_query_strips_inline_comments(tmp_path: Path) -> None:
    use_case = WordbankUseCase(_db_path(tmp_path))

    resolved = use_case.resolve_query("House # comment")

    assert resolved.query_surface == "house"

def test_wordbank_resolve_query_skips_short_letter_words(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({"is": "ice"}, detected_languages={"is": "EN"}),
    )

    resolved = use_case.resolve_query("is")

    assert resolved.query_surface == "is"
    assert resolved.classification == "uncertain"
    assert resolved.word_actions == []
    assert resolved.da_to_en_translation is None
    assert resolved.en_to_da_translation is None

def test_wordbank_resolve_query_supports_optional_flags(tmp_path: Path) -> None:
    translation_service = FakeTranslationService(
        {"house": "hus"},
        detected_languages={"house": "EN"},
    )
    use_case = WordbankUseCase(_db_path(tmp_path), translation_service=translation_service)

    resolved = use_case.resolve_query(
        "House",
        include_translations=False,
        include_language_detection=False,
    )

    assert resolved.en_to_da_translation is None
    assert resolved.da_to_en_translation is None
    assert resolved.query_language is None
    assert resolved.query_language_confidence is None

def test_wordbank_action_payload_is_consistent_between_resolve_query_and_analyze(tmp_path: Path) -> None:
    class HouseNLPAdapter:
        def tokenize(self, text: str) -> list[NLPToken]:
            return [
                NLPToken(
                    text=text,
                    lemma=text.lower(),
                    pos="NOUN",
                    morphology="Gender=Neut|Number=Sing",
                    is_punctuation=False,
                )
            ]

        def lemma_candidates_for_token(self, token: str) -> list[str]:
            return [token.lower()]

        def lemma_for_token(self, token: str) -> str | None:
            return token.lower()

        def metadata(self) -> dict[str, str]:
            return {"adapter": "house-fake"}

    nlp_adapter = HouseNLPAdapter()
    db_path = _db_path(tmp_path)
    use_case = WordbankUseCase(
        db_path,
        translation_service=FakeTranslationService({"house": "hus"}, detected_languages={"house": "EN"}),
        nlp_adapter=nlp_adapter,
    )
    analyze_use_case = AnalyzeNoteUseCase(db_path, nlp_adapter=nlp_adapter)

    resolved = use_case.resolve_query("House", include_translations=False, include_language_detection=False)
    analyzed_tokens = analyze_use_case.execute("House")

    assert len(analyzed_tokens) == 1
    assert resolved.word_actions == analyzed_tokens[0].word_actions
    assert [action.action_type for action in resolved.word_actions] == ["add_as_new"]
    assert resolved.word_actions[0].surface == "house"
    assert resolved.word_actions[0].lemma == "house"
