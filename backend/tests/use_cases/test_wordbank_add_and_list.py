from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.api.schemas.v1.wordbank import LemmaDetailsResponse
from app.db.migrations import get_connection
from app.nlp.adapter import NLPToken
from app.services.use_cases.wordbank import WordbankUseCase
from tests.helpers.factories import _bog_homograph_cor_local, _cor_local_entry, _db_path
from tests.helpers.fakes import (
    FakeCORLocalLexiconService,
    FakeGeminiRelatedWordsService,
    FakeGeminiWordTranslationService,
    FakeTranslationService,
    FakeTTSService,
    FakeVerificationService,
)


def _verify_meaning_targets(use_case: WordbankUseCase, *, lemma: str, meaning_id: int, surfaces: list[str]) -> None:
    use_case.verify_added_word(lemma, None, meaning_id=meaning_id)
    for surface in surfaces:
        use_case.verify_added_word(lemma, surface, meaning_id=meaning_id)


def _variation_gemini(
    lemma: str,
    pos_tag: str,
    gloss: str,
    forms: list[dict[str, str]],
) -> FakeGeminiWordTranslationService:
    return FakeGeminiWordTranslationService(
        {},
        non_cor_variation_overrides={(lemma, pos_tag, gloss): forms},
    )


_BOG_BOOK_FORMS = [
    {"form": "bogen", "pos_tag": "NOUN", "morphology": "Gender=Com|Number=Sing|Definite=Def"},
    {"form": "bøger", "pos_tag": "NOUN", "morphology": "Gender=Com|Number=Plur|Definite=Ind"},
    {"form": "bøgerne", "pos_tag": "NOUN", "morphology": "Gender=Com|Number=Plur|Definite=Def"},
]
_STOR_LARGE_FORMS = [
    {"form": "store", "pos_tag": "ADJ", "morphology": "Degree=Pos|Number=Plur|Definite=Def"},
]
_LAERE_FORMS = [
    {"form": "lærte", "pos_tag": "VERB", "morphology": "Tense=Past|VerbForm=Fin|Voice=Act"},
    {"form": "lær", "pos_tag": "VERB", "morphology": "Mood=Imp|VerbForm=Fin"},
    {"form": "lært", "pos_tag": "VERB", "morphology": "VerbForm=Part|Voice=Act"},
]
_VILLE_FORMS = [
    {"form": "ville", "pos_tag": "VERB", "morphology": "Tense=Past|VerbForm=Fin|Voice=Act"},
    {"form": "villet", "pos_tag": "VERB", "morphology": "VerbForm=Part|Voice=Act"},
]


def _bog_complete_paradigm_cor_local() -> FakeCORLocalLexiconService:
    book_entries = [
        _cor_local_entry(
            cor_id="COR.BOG.BOOK.LEM",
            lemma="bog",
            gloss="book",
            form="bog",
            lemma_idx=123,
            pos_tag="NOUN",
            morphology="Gender=Com|Number=Sing|Definite=Ind",
            gram_raw="sb.fk.sg.ubest",
        ),
        _cor_local_entry(
            cor_id="COR.BOG.BOOK.DEF",
            lemma="bog",
            gloss="book",
            form="bogen",
            lemma_idx=123,
            pos_tag="NOUN",
            morphology="Gender=Com|Number=Sing|Definite=Def",
            gram_raw="sb.fk.sg.best",
        ),
        _cor_local_entry(
            cor_id="COR.BOG.BOOK.PL",
            lemma="bog",
            gloss="book",
            form="bøger",
            lemma_idx=123,
            pos_tag="NOUN",
            morphology="Gender=Com|Number=Plur|Definite=Ind",
            gram_raw="sb.fk.pl.ubest",
        ),
        _cor_local_entry(
            cor_id="COR.BOG.BOOK.PLDEF",
            lemma="bog",
            gloss="book",
            form="bøgerne",
            lemma_idx=123,
            pos_tag="NOUN",
            morphology="Gender=Com|Number=Plur|Definite=Def",
            gram_raw="sb.fk.pl.best",
        ),
    ]
    swamp_entries = [
        _cor_local_entry(
            cor_id="COR.BOG.SWAMP.LEM",
            lemma="bog",
            gloss="swamp",
            form="bog",
            lemma_idx=124,
            pos_tag="NOUN",
            morphology="Gender=Com|Number=Sing|Definite=Ind",
            gram_raw="sb.fk.sg.ubest",
        ),
        _cor_local_entry(
            cor_id="COR.BOG.SWAMP.DEF",
            lemma="bog",
            gloss="swamp",
            form="bogen",
            lemma_idx=124,
            pos_tag="NOUN",
            morphology="Gender=Com|Number=Sing|Definite=Def",
            gram_raw="sb.fk.sg.best",
        ),
        _cor_local_entry(
            cor_id="COR.BOG.SWAMP.PL",
            lemma="bog",
            gloss="swamp",
            form="moser",
            lemma_idx=124,
            pos_tag="NOUN",
            morphology="Gender=Com|Number=Plur|Definite=Ind",
            gram_raw="sb.fk.pl.ubest",
        ),
        _cor_local_entry(
            cor_id="COR.BOG.SWAMP.PLDEF",
            lemma="bog",
            gloss="swamp",
            form="moserne",
            lemma_idx=124,
            pos_tag="NOUN",
            morphology="Gender=Com|Number=Plur|Definite=Def",
            gram_raw="sb.fk.pl.best",
        ),
    ]
    return FakeCORLocalLexiconService(
        by_form={
            "bog": [book_entries[0], swamp_entries[0]],
            "bogen": [book_entries[1], swamp_entries[1]],
            "bøger": [book_entries[2]],
            "bøgerne": [book_entries[3]],
            "moser": [swamp_entries[2]],
            "moserne": [swamp_entries[3]],
        },
        by_lemma_idx={
            123: book_entries,
            124: swamp_entries,
        },
    )


def _fader_complete_paradigm_cor_local() -> FakeCORLocalLexiconService:
    entries = [
        _cor_local_entry(
            cor_id="COR.FADER.LEM",
            lemma="fader",
            gloss="father",
            form="fader",
            lemma_idx=410,
            pos_tag="NOUN",
            morphology="Gender=Com|Number=Sing|Definite=Ind",
            gram_raw="sb.fk.sg.ubest",
        ),
        _cor_local_entry(
            cor_id="COR.FADER.IRREG",
            lemma="fader",
            gloss="father",
            form="far",
            lemma_idx=410,
            pos_tag="NOUN",
            morphology="Gender=Com|Number=Sing|Definite=Ind",
            gram_raw="sb.fk.sg.ubest",
        ),
        _cor_local_entry(
            cor_id="COR.FADER.DEF",
            lemma="fader",
            gloss="father",
            form="faderen",
            lemma_idx=410,
            pos_tag="NOUN",
            morphology="Gender=Com|Number=Sing|Definite=Def",
            gram_raw="sb.fk.sg.best",
        ),
        _cor_local_entry(
            cor_id="COR.FADER.PL",
            lemma="fader",
            gloss="father",
            form="fædre",
            lemma_idx=410,
            pos_tag="NOUN",
            morphology="Gender=Com|Number=Plur|Definite=Ind",
            gram_raw="sb.fk.pl.ubest",
        ),
        _cor_local_entry(
            cor_id="COR.FADER.PLDEF",
            lemma="fader",
            gloss="father",
            form="fædrene",
            lemma_idx=410,
            pos_tag="NOUN",
            morphology="Gender=Com|Number=Plur|Definite=Def",
            gram_raw="sb.fk.pl.best",
        ),
    ]
    return FakeCORLocalLexiconService(
        by_form={entry.form: [entry] for entry in entries},
        by_lemma_idx={410: entries},
    )


def _stor_complete_paradigm_cor_local() -> FakeCORLocalLexiconService:
    large_entries = [
        _cor_local_entry(
            cor_id="COR.STOR.N",
            lemma="stor",
            gloss="large",
            form="stor",
            lemma_idx=220,
            pos_tag="ADJ",
            morphology="Gender=Com|Number=Sing|Definite=Ind",
            gram_raw="adj.sg.ubest.fk",
        ),
        _cor_local_entry(
            cor_id="COR.STOR.T",
            lemma="stor",
            gloss="large",
            form="stort",
            lemma_idx=220,
            pos_tag="ADJ",
            morphology="Gender=Neut|Number=Sing|Definite=Ind",
            gram_raw="adj.sg.ubest.itk",
        ),
        _cor_local_entry(
            cor_id="COR.STOR.DEF",
            lemma="stor",
            gloss="large",
            form="store",
            lemma_idx=220,
            pos_tag="ADJ",
            morphology="Number=Sing|Definite=Def",
            gram_raw="adj.sg.best",
        ),
        _cor_local_entry(
            cor_id="COR.STOR.PL",
            lemma="stor",
            gloss="large",
            form="store",
            lemma_idx=220,
            pos_tag="ADJ",
            morphology="Number=Plur",
            gram_raw="adj.pl",
        ),
    ]
    important_entries = [
        _cor_local_entry(
            cor_id="COR.STOR2.N",
            lemma="stor",
            gloss="important",
            form="stor",
            lemma_idx=221,
            pos_tag="ADJ",
            morphology="Gender=Com|Number=Sing|Definite=Ind",
            gram_raw="adj.sg.ubest.fk",
        ),
        _cor_local_entry(
            cor_id="COR.STOR2.T",
            lemma="stor",
            gloss="important",
            form="stort",
            lemma_idx=221,
            pos_tag="ADJ",
            morphology="Gender=Neut|Number=Sing|Definite=Ind",
            gram_raw="adj.sg.ubest.itk",
        ),
        _cor_local_entry(
            cor_id="COR.STOR2.DEF",
            lemma="stor",
            gloss="important",
            form="store",
            lemma_idx=221,
            pos_tag="ADJ",
            morphology="Number=Sing|Definite=Def",
            gram_raw="adj.sg.best",
        ),
        _cor_local_entry(
            cor_id="COR.STOR2.PL",
            lemma="stor",
            gloss="important",
            form="store",
            lemma_idx=221,
            pos_tag="ADJ",
            morphology="Number=Plur",
            gram_raw="adj.pl",
        ),
    ]
    return FakeCORLocalLexiconService(
        by_form={
            "stor": [large_entries[0], important_entries[0]],
            "stort": [large_entries[1], important_entries[1]],
            "store": [large_entries[2], large_entries[3], important_entries[2], important_entries[3]],
        },
        by_lemma_idx={220: large_entries, 221: important_entries},
    )


def _orange_complete_paradigm_cor_local() -> FakeCORLocalLexiconService:
    entries = [
        _cor_local_entry(
            cor_id="COR.ORANGE.N",
            lemma="orange",
            gloss="orange",
            form="orange",
            lemma_idx=20408,
            pos_tag="ADJ",
            morphology="Gender=Com|Number=Sing|Definite=Ind",
            gram_raw="adj.sg.ubest.fk",
        ),
        _cor_local_entry(
            cor_id="COR.ORANGE.T",
            lemma="orange",
            gloss="orange",
            form="orange",
            lemma_idx=20408,
            pos_tag="ADJ",
            morphology="Gender=Neut|Number=Sing|Definite=Ind",
            gram_raw="adj.sg.ubest.itk",
        ),
        _cor_local_entry(
            cor_id="COR.ORANGE.DEF",
            lemma="orange",
            gloss="orange",
            form="orange",
            lemma_idx=20408,
            pos_tag="ADJ",
            morphology="Number=Sing|Definite=Def",
            gram_raw="adj.sg.best",
        ),
        _cor_local_entry(
            cor_id="COR.ORANGE.PL",
            lemma="orange",
            gloss="orange",
            form="orange",
            lemma_idx=20408,
            pos_tag="ADJ",
            morphology="Number=Plur",
            gram_raw="adj.pl",
        ),
    ]
    return FakeCORLocalLexiconService(by_form={"orange": entries}, by_lemma_idx={20408: entries})


def _laere_complete_paradigm_cor_local() -> FakeCORLocalLexiconService:
    entries = [
        _cor_local_entry(
            cor_id="COR.LAERE.INF",
            lemma="lære",
            gloss="learn",
            form="lære",
            lemma_idx=30686,
            pos_tag="VERB",
            morphology="VerbForm=Inf|Voice=Act",
            gram_raw="vb.inf.akt",
        ),
        _cor_local_entry(
            cor_id="COR.LAERE.PRES",
            lemma="lære",
            gloss="learn",
            form="lærer",
            lemma_idx=30686,
            pos_tag="VERB",
            morphology="Tense=Pres|VerbForm=Fin|Voice=Act",
            gram_raw="vb.præs.akt",
        ),
        _cor_local_entry(
            cor_id="COR.LAERE.PAST",
            lemma="lære",
            gloss="learn",
            form="lærte",
            lemma_idx=30686,
            pos_tag="VERB",
            morphology="Tense=Past|VerbForm=Fin|Voice=Act",
            gram_raw="vb.præt.akt",
        ),
        _cor_local_entry(
            cor_id="COR.LAERE.IMP",
            lemma="lære",
            gloss="learn",
            form="lær",
            lemma_idx=30686,
            pos_tag="VERB",
            morphology="Mood=Imp|VerbForm=Fin",
            gram_raw="vb.imp",
        ),
        _cor_local_entry(
            cor_id="COR.LAERE.PART",
            lemma="lære",
            gloss="learn",
            form="lært",
            lemma_idx=30686,
            pos_tag="VERB",
            morphology="VerbForm=Part|Voice=Act",
            gram_raw="vb.perf.part",
        ),
    ]
    return FakeCORLocalLexiconService(
        by_form={entry.form: [entry] for entry in entries},
        by_lemma_idx={30686: entries},
    )


def test_wordbank_use_case_round_trip(tmp_path: Path) -> None:
    use_case = WordbankUseCase(_db_path(tmp_path))

    added = use_case.add_word("Bogen", "bog")
    assert added.status == "inserted"
    assert added.stored_lemma == "bog"
    assert added.stored_surface_form == "bogen"

    details = use_case.get_lemma_details("bog")
    assert details.lemma == "bog"
    assert details.is_sectioned is True
    assert [item.form for item in details.surface_forms] == ["bog"]
    assert len(details.meaning_sections) == 1
    assert details.meaning_sections[0].meaning_key == "bog"
    assert [item.form for item in details.meaning_sections[0].surface_forms] == ["bogen"]

    listing = use_case.list_lemmas()
    assert listing.items[0].lemma == "bog"
    assert listing.items[0].display_lemma == "bog"
    assert listing.items[0].variation_count == 1
    assert listing.items[0].english_translation is None


def test_wordbank_add_word_uses_static_pronoun_metadata(tmp_path: Path) -> None:
    translation_service = FakeTranslationService({"du": "provider should not be used"})
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        translation_service=translation_service,
        cor_local_lexicon_service=FakeCORLocalLexiconService(),
    )

    added = use_case.add_word("Du", "du")
    details = use_case.get_lemma_details("du")
    listing = use_case.list_lemmas()

    assert added.status == "inserted"
    assert added.verification is None
    assert added.queued_verification_targets == []
    assert added.queued_pronunciation_forms == []
    assert translation_service.calls == []
    assert details.english_translation == "you"
    assert details.pos_tag == "PRON"
    assert details.morphology == "PronType=Prs|Case=Nom|Person=2|Number=Sing"
    assert [form.form for form in details.surface_forms] == ["du"]
    assert [item.lemma for item in listing.items] == []


def test_wordbank_starter_categories_are_seeded_once(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    _ = WordbankUseCase(db_path)

    with get_connection(db_path) as conn:
        count_before = conn.execute("SELECT COUNT(*) AS count FROM wordbank_categories").fetchone()
        labels_before = [
            row["label"]
            for row in conn.execute("SELECT label FROM wordbank_categories ORDER BY normalized_label").fetchall()
        ]
    assert count_before is not None
    assert count_before["count"] == 67
    assert "Actions" not in labels_before
    assert {"Furniture", "Emotion", "Plant", "Communication", "Learning", "Grammar"}.issubset(labels_before)

    _ = WordbankUseCase(db_path)

    with get_connection(db_path) as conn:
        count_after = conn.execute("SELECT COUNT(*) AS count FROM wordbank_categories").fetchone()
    assert count_after is not None
    assert count_after["count"] == 67

def test_wordbank_use_case_facade_delegates_across_extracted_workflows(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        translation_service=FakeTranslationService({"bog": "book", "bogen": "the book"}),
    )

    added = use_case.add_word("Bogen", "bog")
    listing = use_case.list_lemmas()
    search = use_case.search_lemmas("bog")
    details = use_case.get_lemma_details("bog")

    assert added.status == "inserted"
    assert listing.items[0].lemma == "bog"
    assert search.items[0].lemma == "bog"
    assert details.lemma == "bog"
    assert details.english_translation == "book"
    assert details.is_sectioned is True
    assert len(details.meaning_sections) == 1
    assert details.meaning_sections[0].surface_forms[0].lemma_translation == "book"

def test_wordbank_use_case_includes_pos_and_morphology_when_nlp_available(tmp_path: Path) -> None:
    class WordbankNLPAdapter:
        def tokenize(self, text: str) -> list[NLPToken]:
            return [
                NLPToken(
                    text=text,
                    lemma=text.lower(),
                    pos="NOUN",
                    morphology="Gender=Com|Number=Sing",
                    is_punctuation=False,
                )
            ]

        def lemma_candidates_for_token(self, token: str) -> list[str]:
            return [token.lower()]

        def lemma_for_token(self, token: str) -> str | None:
            return token.lower()

        def metadata(self) -> dict[str, str]:
            return {"adapter": "wordbank-fake"}

    use_case = WordbankUseCase(
        _db_path(tmp_path),
        nlp_adapter=WordbankNLPAdapter(),
    )

    use_case.add_word("Bogen", "bog")

    details = use_case.get_lemma_details("bog")
    assert details.pos_tag == "NOUN"
    assert details.morphology == "Gender=Com|Number=Sing"
    assert details.is_sectioned is True
    assert len(details.surface_forms) == 1
    assert details.surface_forms[0].form == "bog"
    assert details.surface_forms[0].pos_tag == "NOUN"
    assert details.surface_forms[0].morphology == "Gender=Com|Number=Sing"
    assert len(details.meaning_sections) == 1
    assert details.meaning_sections[0].pos_tag == "NOUN"
    assert details.meaning_sections[0].morphology == "Gender=Com|Number=Sing"
    assert details.meaning_sections[0].surface_forms == [
        LemmaDetailsResponse.SurfaceFormDetails(
            form="bogen",
            pos_tag="NOUN",
            morphology="Gender=Com|Number=Sing",
            lemma="bog",
            lemma_translation=None,
        ),
    ]

def test_wordbank_list_lemmas_displays_verbs_with_at_prefix(tmp_path: Path) -> None:
    class VerbListNLPAdapter:
        def tokenize(self, text: str) -> list[NLPToken]:
            return [
                NLPToken(
                    text=text,
                    lemma=text.lower(),
                    pos="VERB",
                    morphology="VerbForm=Inf",
                    is_punctuation=False,
                )
            ]

        def lemma_candidates_for_token(self, token: str) -> list[str]:
            return [token.lower()]

        def lemma_for_token(self, token: str) -> str | None:
            return token.lower()

        def metadata(self) -> dict[str, str]:
            return {"adapter": "verb-list-fake"}

    use_case = WordbankUseCase(
        _db_path(tmp_path),
        nlp_adapter=VerbListNLPAdapter(),
    )
    use_case.add_word("laver", "lave")

    listing = use_case.list_lemmas()
    assert listing.items[0].lemma == "lave"
    assert listing.items[0].display_lemma == "at lave"

def test_wordbank_add_word_keeps_same_surface_under_distinct_meaning_sections(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=_bog_homograph_cor_local(),
        translation_service=FakeTranslationService(
            {
                "book": "book",
                "swamp": "swamp",
                "bog": "book-fallback",
                "bogen": "generic-bogen",
            }
        ),
        gemini_word_translation_service=FakeGeminiWordTranslationService(
            {
                ("bog", "bog", "book"): "book",
                ("bogen", "bog", "book"): "the book",
                ("bog", "bog", "swamp"): "swamp",
                ("bogen", "bog", "swamp"): "the swamp",
            }
        ),
    )

    first = use_case.add_word("Bogen", "bog", cor_id="COR.BOG.BOOK.DEF")
    second = use_case.add_word("Bogen", "bog", cor_id="COR.BOG.SWAMP.DEF")
    details = use_case.get_lemma_details("bog")

    assert first.status == "inserted"
    assert second.status == "inserted"
    assert first.meaning is not None
    assert second.meaning is not None
    assert first.meaning.id != second.meaning.id
    assert [section.meaning_key for section in details.meaning_sections] == ["book", "swamp"]
    assert details.meaning_sections[0].surface_forms[0].lemma_translation == "book"
    assert details.meaning_sections[1].surface_forms[0].lemma_translation == "swamp"


def test_wordbank_add_word_separates_different_pos_homographs(tmp_path: Path) -> None:
    # 1. noun: kort (map, lemma_idx 1001)
    noun_lemma = _cor_local_entry(
        cor_id="COR.KORT.NOUN.LEM",
        lemma="kort",
        gloss="map",
        form="kort",
        lemma_idx=1001,
        pos_tag="NOUN",
        morphology="Gender=Neut|Number=Sing|Definite=Ind",
    )
    noun_surface = _cor_local_entry(
        cor_id="COR.KORT.NOUN.DEF",
        lemma="kort",
        gloss="map",
        form="kortet",
        lemma_idx=1001,
        pos_tag="NOUN",
        morphology="Gender=Neut|Number=Sing|Definite=Def",
    )
    # 2. adjective: kort (short, lemma_idx 1002)
    adj_lemma = _cor_local_entry(
        cor_id="COR.KORT.ADJ.LEM",
        lemma="kort",
        gloss="short",
        form="kort",
        lemma_idx=1002,
        pos_tag="ADJ",
        morphology="Gender=Com|Number=Sing|Definite=Ind",
    )
    adj_surface = _cor_local_entry(
        cor_id="COR.KORT.ADJ.NEUT",
        lemma="kort",
        gloss="short",
        form="kortet",
        lemma_idx=1002,
        pos_tag="ADJ",
        morphology="Gender=Neut|Number=Sing|Definite=Ind",
    )

    fake_cor = FakeCORLocalLexiconService(
        by_form={
            "kort": [noun_lemma, adj_lemma],
            "kortet": [noun_surface, adj_surface],
        },
        by_lemma_idx={
            1001: [noun_lemma, noun_surface],
            1002: [adj_lemma, adj_surface],
        },
    )

    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=fake_cor,
        translation_service=FakeTranslationService(
            {
                "map": "map",
                "short": "short",
            }
        ),
        gemini_word_translation_service=FakeGeminiWordTranslationService(
            {
                ("kort", "kort", "map"): "map",
                ("kort", "kort", "short"): "short",
            }
        ),
    )

    first = use_case.add_word("kort", "kort", cor_id="COR.KORT.NOUN.LEM")
    second = use_case.add_word("kort", "kort", cor_id="COR.KORT.ADJ.LEM")
    details = use_case.get_lemma_details("kort")

    assert first.status == "inserted"
    assert second.status == "inserted"
    assert first.meaning is not None
    assert second.meaning is not None
    assert first.meaning.id != second.meaning.id

    assert len(details.meaning_sections) == 2
    assert details.meaning_sections[0].pos_tag == "NOUN"
    assert details.meaning_sections[0].meaning_key == "map"
    assert details.meaning_sections[1].pos_tag == "ADJ"
    assert details.meaning_sections[1].meaning_key == "short"


def test_wordbank_add_word_treats_duplicate_cor_id_for_same_meaning_form_as_exists(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=_bog_homograph_cor_local(),
    )

    first = use_case.add_word("Bogen", "bog", cor_id="COR.BOG.BOOK.DEF")
    second = use_case.add_word("Bogen", "bog", cor_id="COR.BOG.BOOK.DEF")

    assert first.status == "inserted"
    assert second.status == "exists"

def test_wordbank_add_word_routes_variations_to_their_matching_meaning(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=_bog_homograph_cor_local(),
        translation_service=FakeTranslationService({"book": "book", "swamp": "swamp"}),
        gemini_word_translation_service=FakeGeminiWordTranslationService(
            {
                ("bog", "bog", "book"): "book",
                ("bogen", "bog", "book"): "the book",
                ("bøger", "bog", "book"): "books",
                ("bog", "bog", "swamp"): "swamp",
                ("moser", "bog", "swamp"): "swamps",
            }
        ),
    )

    use_case.add_word("Bogen", "bog", cor_id="COR.BOG.BOOK.DEF")
    use_case.add_word("Moser", "bog", cor_id="COR.BOG.SWAMP.PL")
    details = use_case.get_lemma_details("bog")

    by_key = {section.meaning_key: section for section in details.meaning_sections}
    assert [item.form for item in by_key["book"].surface_forms] == ["bogen"]
    assert [item.form for item in by_key["swamp"].surface_forms] == ["moser"]
    assert by_key["swamp"].surface_forms[0].lemma_translation == "swamp"


def test_complete_meaning_variations_backfills_missing_noun_slots_for_search_seed_entries(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    use_case = WordbankUseCase(
        db_path,
        cor_local_lexicon_service=_bog_complete_paradigm_cor_local(),
        gemini_word_translation_service=_variation_gemini("bog", "NOUN", "book", _BOG_BOOK_FORMS),
        verification_service=FakeVerificationService(),
        tts_service=FakeTTSService({}),
    )

    added = use_case.add_word(
        "bøger",
        "bog",
        search_seed={
            "lemma": "bog",
            "surface": "bøger",
            "cor_id": "COR.BOG.BOOK.PL",
            "cor_lemma_idx": 123,
            "meaning_key": "book",
            "gloss": "book",
            "english_translation": "book",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Plur|Definite=Ind",
        },
    )
    assert added.meaning is not None
    _verify_meaning_targets(use_case, lemma="bog", meaning_id=added.meaning.id, surfaces=["bøger"])

    response = use_case.complete_meaning_variations("bog", meaning_id=added.meaning.id)

    assert response.status == "updated"
    assert response.queued_verification_targets == []
    assert response.added_surface_forms == ["bogen", "bøgerne"]
    assert response.queued_pronunciation_forms == ["bog", "bogen", "bøgerne"]

    details = use_case.get_lemma_details("bog")
    assert [form.form for form in details.meaning_sections[0].surface_forms] == ["bogen", "bøger", "bøgerne"]
    assert details.surface_forms == []

    with get_connection(db_path) as conn:
        jobs = conn.execute(
            """
            SELECT dedupe_key, payload_json
            FROM wordbank_background_jobs
            WHERE job_type = 'generate_pronunciation'
            ORDER BY dedupe_key ASC
            """
        ).fetchall()
    assert [str(row["dedupe_key"]) for row in jobs] == ["generate_pronunciation::bog"]
    assert json.loads(str(jobs[0]["payload_json"])) == {
        "force": False,
        "requested_forms": ["bog", "bøger", "bogen", "bøgerne"],
        "stored_lemma": "bog",
    }


def test_complete_meaning_variations_uses_selected_homograph_meaning_only(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=_bog_complete_paradigm_cor_local(),
        gemini_word_translation_service=_variation_gemini("bog", "NOUN", "book", _BOG_BOOK_FORMS),
        verification_service=FakeVerificationService(),
    )

    first = use_case.add_word(
        "bogen",
        "bog",
        search_seed={
            "lemma": "bog",
            "surface": "bogen",
            "cor_id": "COR.BOG.BOOK.DEF",
            "cor_lemma_idx": 123,
            "meaning_key": "book",
            "gloss": "book",
            "english_translation": "book",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Sing|Definite=Def",
        },
    )
    second = use_case.add_word(
        "bogen",
        "bog",
        search_seed={
            "lemma": "bog",
            "surface": "bogen",
            "cor_id": "COR.BOG.SWAMP.DEF",
            "cor_lemma_idx": 124,
            "meaning_key": "swamp",
            "gloss": "swamp",
            "english_translation": "swamp",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Sing|Definite=Def",
        },
    )
    assert first.meaning is not None
    assert second.meaning is not None
    _verify_meaning_targets(use_case, lemma="bog", meaning_id=first.meaning.id, surfaces=["bogen"])

    response = use_case.complete_meaning_variations("bog", meaning_id=first.meaning.id)

    assert response.status == "updated"
    details = use_case.get_lemma_details("bog")
    assert [section.gloss for section in details.meaning_sections] == ["book", "swamp"]
    assert [form.form for form in details.meaning_sections[0].surface_forms] == ["bogen", "bøger", "bøgerne"]
    assert [form.form for form in details.meaning_sections[1].surface_forms] == ["bogen"]


def test_complete_meaning_variations_backfills_missing_adjective_slots_for_search_seed_entries(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    use_case = WordbankUseCase(
        db_path,
        cor_local_lexicon_service=_stor_complete_paradigm_cor_local(),
        gemini_word_translation_service=_variation_gemini("stor", "ADJ", "large", _STOR_LARGE_FORMS),
        verification_service=FakeVerificationService(),
        tts_service=FakeTTSService({}),
    )

    added = use_case.add_word(
        "stort",
        "stor",
        search_seed={
            "lemma": "stor",
            "surface": "stort",
            "cor_id": "COR.STOR.T",
            "cor_lemma_idx": 220,
            "meaning_key": "large",
            "gloss": "large",
            "english_translation": "large",
            "pos_tag": "ADJ",
            "morphology": "Gender=Neut|Number=Sing|Definite=Ind",
        },
    )
    assert added.meaning is not None
    _verify_meaning_targets(use_case, lemma="stor", meaning_id=added.meaning.id, surfaces=["stort"])

    response = use_case.complete_meaning_variations("stor", meaning_id=added.meaning.id)

    assert response.status == "updated"
    assert response.added_surface_forms == ["store"]
    assert response.queued_pronunciation_forms == ["stor", "store"]
    assert response.queued_verification_targets == []

    details = use_case.get_lemma_details("stor")
    assert sorted(form.form for form in details.meaning_sections[0].surface_forms) == ["store", "stort"]


def test_complete_meaning_variations_skips_when_adjective_slots_are_already_covered(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=_orange_complete_paradigm_cor_local(),
        gemini_word_translation_service=_variation_gemini("orange", "ADJ", "orange", []),
        verification_service=FakeVerificationService(),
    )

    added = use_case.add_word(
        "orange",
        "orange",
        search_seed={
            "lemma": "orange",
            "surface": "orange",
            "cor_id": "COR.ORANGE.N",
            "cor_lemma_idx": 20408,
            "meaning_key": "orange",
            "gloss": "orange",
            "english_translation": "orange",
            "pos_tag": "ADJ",
            "morphology": "Gender=Com|Number=Sing|Definite=Ind",
        },
    )
    assert added.meaning is not None
    _verify_meaning_targets(use_case, lemma="orange", meaning_id=added.meaning.id, surfaces=["orange"])

    response = use_case.complete_meaning_variations("orange", meaning_id=added.meaning.id)

    assert response.status == "skipped"
    assert response.added_surface_forms == []
    assert response.message == "No missing adjective variations were found for 'orange'."


def test_complete_meaning_variations_uses_selected_adjective_meaning_only(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=_stor_complete_paradigm_cor_local(),
        gemini_word_translation_service=_variation_gemini("stor", "ADJ", "large", _STOR_LARGE_FORMS),
        verification_service=FakeVerificationService(),
    )

    first = use_case.add_word(
        "stort",
        "stor",
        search_seed={
            "lemma": "stor",
            "surface": "stort",
            "cor_id": "COR.STOR.T",
            "cor_lemma_idx": 220,
            "meaning_key": "large",
            "gloss": "large",
            "english_translation": "large",
            "pos_tag": "ADJ",
            "morphology": "Gender=Neut|Number=Sing|Definite=Ind",
        },
    )
    second = use_case.add_word(
        "store",
        "stor",
        search_seed={
            "lemma": "stor",
            "surface": "store",
            "cor_id": "COR.STOR2.DEF",
            "cor_lemma_idx": 221,
            "meaning_key": "important",
            "gloss": "important",
            "english_translation": "important",
            "pos_tag": "ADJ",
            "morphology": "Number=Sing|Definite=Def",
        },
    )
    assert first.meaning is not None
    assert second.meaning is not None
    _verify_meaning_targets(use_case, lemma="stor", meaning_id=first.meaning.id, surfaces=["stort"])

    response = use_case.complete_meaning_variations("stor", meaning_id=first.meaning.id)

    assert response.status == "updated"
    details = use_case.get_lemma_details("stor")
    assert [section.gloss for section in details.meaning_sections] == ["large", "important"]
    assert sorted(form.form for form in details.meaning_sections[0].surface_forms) == ["store", "stort"]
    assert sorted(form.form for form in details.meaning_sections[1].surface_forms) == ["store"]


def test_complete_meaning_variations_backfills_missing_verb_slots_for_search_seed_entries(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    use_case = WordbankUseCase(
        db_path,
        cor_local_lexicon_service=_laere_complete_paradigm_cor_local(),
        gemini_word_translation_service=_variation_gemini("lære", "VERB", "learn", _LAERE_FORMS),
        verification_service=FakeVerificationService(),
        tts_service=FakeTTSService({}),
    )

    added = use_case.add_word(
        "lærer",
        "lære",
        search_seed={
            "lemma": "lære",
            "surface": "lærer",
            "cor_id": "COR.LAERE.PRES",
            "cor_lemma_idx": 30686,
            "meaning_key": "learn",
            "gloss": "learn",
            "english_translation": "learn",
            "pos_tag": "VERB",
            "morphology": "Tense=Pres|VerbForm=Fin|Voice=Act",
        },
    )
    assert added.meaning is not None
    _verify_meaning_targets(use_case, lemma="lære", meaning_id=added.meaning.id, surfaces=["lærer"])

    response = use_case.complete_meaning_variations("lære", meaning_id=added.meaning.id)

    assert response.status == "updated"
    assert response.added_surface_forms == ["lærte", "lær", "lært"]
    assert response.queued_pronunciation_forms == ["lære", "lærte", "lær", "lært"]
    assert response.queued_verification_targets == []

    details = use_case.get_lemma_details("lære")
    assert sorted(form.form for form in details.meaning_sections[0].surface_forms) == ["lær", "lærer", "lært", "lærte"]


def test_complete_meaning_variations_persists_same_spelling_verb_slots(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    use_case = WordbankUseCase(
        db_path,
        gemini_word_translation_service=_variation_gemini("ville", "VERB", "want", _VILLE_FORMS),
        verification_service=FakeVerificationService(),
        tts_service=FakeTTSService({}),
    )

    added = use_case.add_word(
        "vil",
        "ville",
        search_seed={
            "lemma": "ville",
            "surface": "vil",
            "cor_id": "COR.VILLE.PRES",
            "cor_lemma_idx": 930,
            "meaning_key": "want",
            "gloss": "want",
            "english_translation": "to want to",
            "pos_tag": "VERB",
            "morphology": "Tense=Pres|VerbForm=Fin|Voice=Act",
        },
    )
    assert added.meaning is not None
    _verify_meaning_targets(use_case, lemma="ville", meaning_id=added.meaning.id, surfaces=["vil"])

    response = use_case.complete_meaning_variations("ville", meaning_id=added.meaning.id)

    assert response.status == "updated"
    assert response.added_surface_forms == ["ville", "villet"]
    assert response.queued_pronunciation_forms == ["ville", "villet"]
    assert response.queued_verification_targets == []

    details = use_case.get_lemma_details("ville")
    surface_forms = details.meaning_sections[0].surface_forms
    assert details.meaning_sections[0].gloss_translation is None
    assert sorted(form.form for form in surface_forms) == ["vil", "ville", "villet"]
    assert any(
        form.form == "ville" and form.morphology == "Tense=Past|VerbForm=Fin|Voice=Act" for form in surface_forms
    )


def test_complete_meaning_variations_skips_when_verb_slots_are_already_covered(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=_laere_complete_paradigm_cor_local(),
        gemini_word_translation_service=_variation_gemini("lære", "VERB", "learn", _LAERE_FORMS),
        verification_service=FakeVerificationService(),
    )

    for surface, cor_id, morphology in [
        ("lærer", "COR.LAERE.PRES", "Tense=Pres|VerbForm=Fin|Voice=Act"),
        ("lærte", "COR.LAERE.PAST", "Tense=Past|VerbForm=Fin|Voice=Act"),
        ("lær", "COR.LAERE.IMP", "Mood=Imp|VerbForm=Fin"),
        ("lært", "COR.LAERE.PART", "VerbForm=Part|Voice=Act"),
    ]:
        added = use_case.add_word(
            surface,
            "lære",
            search_seed={
                "lemma": "lære",
                "surface": surface,
                "cor_id": cor_id,
                "cor_lemma_idx": 30686,
                "meaning_key": "learn",
                "gloss": "learn",
                "english_translation": "learn",
                "pos_tag": "VERB",
                "morphology": morphology,
            },
        )
    assert added.meaning is not None
    _verify_meaning_targets(use_case, lemma="lære", meaning_id=added.meaning.id, surfaces=["lærer", "lærte", "lær", "lært"])

    response = use_case.complete_meaning_variations("lære", meaning_id=added.meaning.id)

    assert response.status == "skipped"
    assert response.added_surface_forms == []
    assert response.message == "No missing verb variations were found for 'lære'."


def test_get_lemma_details_orders_standard_noun_variations_in_slot_order(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=_bog_complete_paradigm_cor_local(),
        gemini_word_translation_service=_variation_gemini("bog", "NOUN", "book", _BOG_BOOK_FORMS),
        verification_service=FakeVerificationService(),
    )

    for surface, cor_id, morphology in [
        ("bøger", "COR.BOG.BOOK.PL", "Gender=Com|Number=Plur|Definite=Ind"),
        ("bøgerne", "COR.BOG.BOOK.PLDEF", "Gender=Com|Number=Plur|Definite=Def"),
        ("bogen", "COR.BOG.BOOK.DEF", "Gender=Com|Number=Sing|Definite=Def"),
    ]:
        use_case.add_word(
            surface,
            "bog",
            search_seed={
                "lemma": "bog",
                "surface": surface,
                "cor_id": cor_id,
                "cor_lemma_idx": 123,
                "meaning_key": "book",
                "gloss": "book",
                "english_translation": "book",
                "pos_tag": "NOUN",
                "morphology": morphology,
            },
        )

    details = use_case.get_lemma_details("bog")

    assert [form.form for form in details.meaning_sections[0].surface_forms] == ["bogen", "bøger", "bøgerne"]


def test_get_lemma_details_keeps_irregular_other_variations_before_standard_noun_slots(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=_fader_complete_paradigm_cor_local(),
    )

    for surface, cor_id, morphology in [
        ("fædrene", "COR.FADER.PLDEF", "Gender=Com|Number=Plur|Definite=Def"),
        ("far", "COR.FADER.IRREG", "Gender=Com|Number=Sing|Definite=Ind"),
        ("faderen", "COR.FADER.DEF", "Gender=Com|Number=Sing|Definite=Def"),
        ("fædre", "COR.FADER.PL", "Gender=Com|Number=Plur|Definite=Ind"),
    ]:
        use_case.add_word(
            surface,
            "fader",
            search_seed={
                "lemma": "fader",
                "surface": surface,
                "cor_id": cor_id,
                "cor_lemma_idx": 410,
                "meaning_key": "father",
                "gloss": "father",
                "english_translation": "father",
                "pos_tag": "NOUN",
                "morphology": morphology,
            },
        )

    details = use_case.get_lemma_details("fader")

    assert [form.form for form in details.meaning_sections[0].surface_forms] == ["far", "faderen", "fædre", "fædrene"]


def test_complete_meaning_variations_skips_when_already_complete_or_cor_identity_missing(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=_bog_complete_paradigm_cor_local(),
        gemini_word_translation_service=_variation_gemini("bog", "NOUN", "book", _BOG_BOOK_FORMS),
        verification_service=FakeVerificationService(),
    )

    added = use_case.add_word(
        "bøgerne",
        "bog",
        search_seed={
            "lemma": "bog",
            "surface": "bøgerne",
            "cor_id": "COR.BOG.BOOK.PLDEF",
            "cor_lemma_idx": 123,
            "meaning_key": "book",
            "gloss": "book",
            "english_translation": "book",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Plur|Definite=Def",
        },
    )
    assert added.meaning is not None
    _verify_meaning_targets(use_case, lemma="bog", meaning_id=added.meaning.id, surfaces=["bøgerne"])
    updated = use_case.complete_meaning_variations("bog", meaning_id=added.meaning.id)
    _verify_meaning_targets(use_case, lemma="bog", meaning_id=added.meaning.id, surfaces=["bogen", "bøger", "bøgerne"])
    skipped = use_case.complete_meaning_variations("bog", meaning_id=added.meaning.id)

    assert updated.status == "updated"
    assert skipped.status == "skipped"
    assert skipped.added_surface_forms == []

    manual_dir = tmp_path / "manual"
    manual_dir.mkdir()
    manual_use_case = WordbankUseCase(_db_path(manual_dir), verification_service=FakeVerificationService())
    manual = manual_use_case.add_word(
        "Bogen",
        "bog",
        search_seed={
            "lemma": "bog",
            "surface": "bogen",
            "cor_id": "COR.BOG.BOOK.DEF",
            "cor_lemma_idx": None,
            "meaning_key": "book",
            "gloss": "book",
            "english_translation": "book",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Sing|Definite=Def",
        },
    )
    assert manual.meaning is not None
    _verify_meaning_targets(manual_use_case, lemma="bog", meaning_id=manual.meaning.id, surfaces=["bogen"])

    missing_identity = manual_use_case.complete_meaning_variations("bog", meaning_id=manual.meaning.id)

    assert missing_identity.status == "skipped"
    assert "Gemini" in missing_identity.message


def test_complete_meaning_variations_does_not_requeue_verification_review(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    use_case = WordbankUseCase(
        db_path,
        cor_local_lexicon_service=_bog_complete_paradigm_cor_local(),
        gemini_word_translation_service=_variation_gemini("bog", "NOUN", "book", _BOG_BOOK_FORMS),
        verification_service=FakeVerificationService(),
    )

    added = use_case.add_word(
        "bøger",
        "bog",
        search_seed={
            "lemma": "bog",
            "surface": "bøger",
            "cor_id": "COR.BOG.BOOK.PL",
            "cor_lemma_idx": 123,
            "meaning_key": "book",
            "gloss": "book",
            "english_translation": "book",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Plur|Definite=Ind",
        },
    )
    assert added.meaning is not None
    _verify_meaning_targets(use_case, lemma="bog", meaning_id=added.meaning.id, surfaces=["bøger"])

    with get_connection(db_path) as conn:
        before_rows = conn.execute(
            """
            SELECT dedupe_key, payload_json
            FROM wordbank_background_jobs
            WHERE job_type = 'verify_word'
            ORDER BY id ASC
            """
        ).fetchall()

    response = use_case.complete_meaning_variations("bog", meaning_id=added.meaning.id)

    assert response.status == "updated"

    with get_connection(db_path) as conn:
        after_rows = conn.execute(
            """
            SELECT dedupe_key, payload_json
            FROM wordbank_background_jobs
            WHERE job_type = 'verify_word'
            ORDER BY id ASC
            """
        ).fetchall()
        verification_rows = conn.execute(
            """
            SELECT meaning_id, stored_surface_form, status
            FROM wordbank_verification_records
            ORDER BY id ASC
            """
        ).fetchall()

    assert after_rows == before_rows
    assert [(row["meaning_id"], row["stored_surface_form"], row["status"]) for row in verification_rows] == [
        (added.meaning.id, None, "verified"),
        (added.meaning.id, "bøger", "verified"),
    ]

    details = use_case.get_lemma_details("bog")
    assert details.meaning_sections[0].verification is not None
    assert details.meaning_sections[0].verification.status == "verified"
    assert any(form.verification is not None for form in details.meaning_sections[0].surface_forms)


@pytest.mark.parametrize("provider", ["azure_translator", "deepl_translator"])
def test_wordbank_add_word_normalizes_framed_single_word_translation_for_all_providers(
    tmp_path: Path,
    provider: str,
) -> None:
    vin_entry = _cor_local_entry(
        cor_id="COR.VIN.110.01",
        lemma="vin",
        gloss=None,
        form="vin",
        lemma_idx=64001,
        pos_tag="NOUN",
        morphology="Gender=Neut|Number=Sing|Definite=Ind",
        gram_raw="sb.itk.sg.ubest",
    )
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_form={"vin": [vin_entry]},
            by_lemma_idx={64001: [vin_entry]},
        ),
        translation_service=FakeTranslationService({"et vin": "in wine"}, provider=provider),
    )

    use_case.add_word("Vin", "vin", cor_id="COR.VIN.110.01")

    listing = use_case.list_lemmas()
    details = use_case.get_lemma_details("vin")

    assert listing.items[0].english_translation == "wine"
    assert details.english_translation == "wine"

def test_wordbank_add_word_applies_selected_pos_and_morphology(tmp_path: Path) -> None:
    use_case = WordbankUseCase(_db_path(tmp_path))

    use_case.add_word(
        "Gift",
        "gifte",
        pos_tag="verb",
        morphology="Mood=Imp|VerbForm=Fin",
    )

    details = use_case.get_lemma_details("gifte")
    assert details.pos_tag == "VERB"
    assert details.morphology == "Mood=Imp|VerbForm=Fin"
    assert details.surface_forms[0].pos_tag == "VERB"
    assert details.surface_forms[0].morphology == "Mood=Imp|VerbForm=Fin"

def test_wordbank_add_word_stores_lemma_form_when_surface_differs(tmp_path: Path) -> None:
    use_case = WordbankUseCase(_db_path(tmp_path))

    use_case.add_word(
        "lærer",
        "lære",
        pos_tag="VERB",
        morphology="Tense=Pres|VerbForm=Fin|Voice=Act",
    )

    details = use_case.get_lemma_details("lære")
    forms = {item.form: item for item in details.surface_forms}
    assert "lærer" in forms
    assert "lære" in forms
    assert forms["lærer"].morphology == "Tense=Pres|VerbForm=Fin|Voice=Act"

def test_wordbank_list_lemmas_uses_stored_pos_metadata_without_runtime_tokenization(tmp_path: Path) -> None:
    class CountingNLPAdapter:
        def __init__(self) -> None:
            self.calls = 0

        def tokenize(self, text: str) -> list[NLPToken]:
            self.calls += 1
            return [
                NLPToken(
                    text=text,
                    lemma=text.lower(),
                    pos="VERB",
                    morphology="VerbForm=Inf",
                    is_punctuation=False,
                )
            ]

        def lemma_candidates_for_token(self, token: str) -> list[str]:
            return [token.lower()]

        def lemma_for_token(self, token: str) -> str | None:
            return token.lower()

        def metadata(self) -> dict[str, str]:
            return {"adapter": "counting"}

    adapter = CountingNLPAdapter()
    use_case = WordbankUseCase(_db_path(tmp_path), nlp_adapter=adapter)

    use_case.add_word("Laver", "lave")
    calls_after_add = adapter.calls

    listing = use_case.list_lemmas()

    assert listing.items[0].display_lemma == "at lave"
    assert adapter.calls == calls_after_add

def test_wordbank_get_lemma_details_persists_extracted_pos_and_morphology_for_forms(tmp_path: Path) -> None:
    class CountingNLPAdapter:
        def __init__(self) -> None:
            self.calls = 0

        def tokenize(self, text: str) -> list[NLPToken]:
            self.calls += 1
            return [
                NLPToken(
                    text=text,
                    lemma=text.lower(),
                    pos="NOUN",
                    morphology="Number=Sing",
                    is_punctuation=False,
                )
            ]

        def lemma_candidates_for_token(self, token: str) -> list[str]:
            return [token.lower()]

        def lemma_for_token(self, token: str) -> str | None:
            return token.lower()

        def metadata(self) -> dict[str, str]:
            return {"adapter": "counting"}

    adapter = CountingNLPAdapter()
    use_case = WordbankUseCase(_db_path(tmp_path), nlp_adapter=adapter)

    use_case.add_word("Bogen", "bog")

    details_first = use_case.get_lemma_details("bog")
    assert details_first.pos_tag == "NOUN"
    assert details_first.is_sectioned is True
    assert details_first.meaning_sections[0].surface_forms[0].pos_tag == "NOUN"

    details_second = use_case.get_lemma_details("bog")
    assert details_second.pos_tag == "NOUN"
    assert details_second.meaning_sections[0].surface_forms[0].morphology == "Number=Sing"


def test_wordbank_search_seed_add_stores_only_selected_search_payload(tmp_path: Path) -> None:
    class CountingNLPAdapter:
        def __init__(self) -> None:
            self.calls = 0

        def tokenize(self, text: str) -> list[NLPToken]:
            self.calls += 1
            return [
                NLPToken(
                    text=text,
                    lemma=text.lower(),
                    pos="NOUN",
                    morphology="Number=Sing",
                    is_punctuation=False,
                )
            ]

        def lemma_candidates_for_token(self, token: str) -> list[str]:
            return [token.lower()]

        def lemma_for_token(self, token: str) -> str | None:
            return token.lower()

        def metadata(self) -> dict[str, str]:
            return {"adapter": "counting"}

    nlp_adapter = CountingNLPAdapter()
    translation_service = FakeTranslationService({"lærere": "teachers"})
    gemini_service = FakeGeminiWordTranslationService({("lærere", "lærer", "teacher"): "teachers"})
    db_path = _db_path(tmp_path)
    use_case = WordbankUseCase(
        db_path,
        nlp_adapter=nlp_adapter,
        translation_service=translation_service,
        gemini_word_translation_service=gemini_service,
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_lemma_idx={
                49032: [
                    _cor_local_entry(
                        cor_id="COR.49032.110.01",
                        lemma="lærer",
                        gloss="teacher",
                        form="lærer",
                        lemma_idx=49032,
                        pos_tag="NOUN",
                        morphology="Gender=Com|Number=Sing|Definite=Ind",
                        gram_raw="sb.fk.sg.ubest",
                    ),
                    _cor_local_entry(
                        cor_id="COR.49032.112.01",
                        lemma="lærer",
                        gloss="teacher",
                        form="lærere",
                        lemma_idx=49032,
                        pos_tag="NOUN",
                        morphology="Gender=Com|Number=Plur|Definite=Ind",
                        gram_raw="sb.fk.pl.ubest",
                    ),
                ],
            },
        ),
    )

    added = use_case.add_word(
        "lærere",
        "lærer",
        search_seed={
            "lemma": "lærer",
            "surface": "lærere",
            "cor_id": "COR.49032.112.01",
            "cor_lemma_idx": 49032,
            "meaning_key": "teacher",
            "gloss": "teacher",
            "english_translation": "teacher",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Plur|Definite=Ind",
        },
    )

    details = use_case.get_lemma_details("lærer")

    assert added.saved_snapshot is not None
    assert translation_service.calls == []
    assert gemini_service.calls == []
    assert gemini_service.batch_calls == []
    assert nlp_adapter.calls == 0
    assert details.is_sectioned is True
    assert details.pos_tag == "NOUN"
    assert details.morphology == "Gender=Com|Number=Sing|Definite=Ind"
    assert details.meaning_sections[0].english_translation == "teacher"
    assert details.meaning_sections[0].morphology == "Gender=Com|Number=Sing|Definite=Ind"
    assert [item.form for item in details.meaning_sections[0].surface_forms] == ["lærere"]
    assert details.meaning_sections[0].surface_forms[0].morphology == "Gender=Com|Number=Plur|Definite=Ind"

    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT form
            FROM surface_forms sf
            JOIN lexemes l ON l.id = sf.lexeme_id
            WHERE l.lemma = ?
            ORDER BY form ASC
            """,
            ("lærer",),
        ).fetchall()
    assert [str(row["form"]) for row in rows] == ["lærere"]


def test_wordbank_search_seed_add_uses_canonical_lemma_metadata_for_verbs(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_lemma_idx={
                30686: [
                    _cor_local_entry(
                        cor_id="COR.30686.200.01",
                        lemma="lære",
                        gloss="learn",
                        form="lære",
                        lemma_idx=30686,
                        pos_tag="VERB",
                        morphology="VerbForm=Inf|Voice=Act",
                        gram_raw="vb.inf.akt",
                    ),
                    _cor_local_entry(
                        cor_id="COR.30686.203.01",
                        lemma="lære",
                        gloss="learn",
                        form="lærer",
                        lemma_idx=30686,
                        pos_tag="VERB",
                        morphology="Tense=Pres|VerbForm=Fin|Voice=Act",
                        gram_raw="vb.præs.akt",
                    ),
                ],
            },
        ),
    )

    added = use_case.add_word(
        "lærer",
        "lære",
        search_seed={
            "lemma": "lære",
            "surface": "lærer",
            "cor_id": "COR.30686.203.01",
            "cor_lemma_idx": 30686,
            "meaning_key": "learn",
            "gloss": "learn",
            "english_translation": "learn",
            "pos_tag": "VERB",
            "morphology": "Tense=Pres|VerbForm=Fin|Voice=Act",
        },
    )

    details = use_case.get_lemma_details("lære")

    assert added.saved_snapshot is not None
    assert added.meaning is not None
    assert added.saved_snapshot.pos_tag == "VERB"
    assert added.saved_snapshot.morphology == "VerbForm=Inf|Voice=Act"
    assert details.pos_tag == "VERB"
    assert details.morphology == "VerbForm=Inf|Voice=Act"
    assert details.is_sectioned is True
    assert len(details.meaning_sections) == 1
    assert details.meaning_sections[0].id == added.meaning.id
    assert details.meaning_sections[0].meaning_key == "learn"
    assert details.meaning_sections[0].pos_tag == "VERB"
    assert details.meaning_sections[0].morphology == "VerbForm=Inf|Voice=Act"
    assert details.meaning_sections[0].gram_raw == "vb.inf.akt"
    assert details.meaning_sections[0].surface_forms == [
        LemmaDetailsResponse.SurfaceFormDetails(
            form="lærer",
            pos_tag="VERB",
            morphology="Tense=Pres|VerbForm=Fin|Voice=Act",
            lemma="lære",
            lemma_translation="learn",
            gloss="learn",
        )
    ]
    assert details.surface_forms == []


def test_wordbank_search_seed_add_blanks_low_confidence_self_translated_verbs(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    use_case = WordbankUseCase(
        db_path,
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_lemma_idx={
                36439: [
                    _cor_local_entry(
                        cor_id="COR.36439.200.01",
                        lemma="bile",
                        gloss=None,
                        form="bile",
                        lemma_idx=36439,
                        pos_tag="VERB",
                        morphology="VerbForm=Inf|Voice=Act",
                        gram_raw="vb.inf.akt",
                    ),
                    _cor_local_entry(
                        cor_id="COR.36439.209.01",
                        lemma="bile",
                        gloss=None,
                        form="bil",
                        lemma_idx=36439,
                        pos_tag="VERB",
                        morphology="Mood=Imp|VerbForm=Fin",
                        gram_raw="vb.imp",
                    ),
                ],
            },
        ),
    )

    added = use_case.add_word(
        "bil",
        "bile",
        search_seed={
            "lemma": "bile",
            "surface": "bil",
            "cor_id": "COR.36439.209.01",
            "cor_lemma_idx": 36439,
            "meaning_key": "bile",
            "gloss": None,
            "english_translation": "to bile",
            "pos_tag": "VERB",
            "morphology": "Mood=Imp|VerbForm=Fin",
        },
    )

    assert added.meaning is not None
    assert added.meaning.english_translation is None

    details = use_case.get_lemma_details("bile")
    assert details.meaning_sections[0].english_translation is None

    with get_connection(db_path) as conn:
        lexeme = conn.execute(
            "SELECT english_translation, translation_provider FROM lexemes WHERE lemma = ?",
            ("bile",),
        ).fetchone()
        meaning = conn.execute(
            "SELECT english_translation FROM lexeme_meanings WHERE lexeme_id = (SELECT id FROM lexemes WHERE lemma = ?)",
            ("bile",),
        ).fetchone()

    assert lexeme is not None
    assert lexeme["english_translation"] is None
    assert lexeme["translation_provider"] is None
    assert meaning is not None
    assert meaning["english_translation"] is None


def test_wordbank_search_seed_details_preserve_merged_gram_raw_for_adjective_lemma_forms(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_lemma_idx={
                20408: [
                    _cor_local_entry(
                        cor_id="COR.20408.300.01",
                        lemma="orange",
                        gloss="orange",
                        form="orange",
                        lemma_idx=20408,
                        pos_tag="ADJ",
                        morphology="Gender=Com|Number=Sing|Definite=Ind",
                        gram_raw="adj.sg.ubest.fk",
                    ),
                    _cor_local_entry(
                        cor_id="COR.20408.301.01",
                        lemma="orange",
                        gloss="orange",
                        form="orange",
                        lemma_idx=20408,
                        pos_tag="ADJ",
                        morphology="Gender=Neut|Number=Sing|Definite=Ind",
                        gram_raw="adj.sg.ubest.itk",
                    ),
                    _cor_local_entry(
                        cor_id="COR.20408.302.01",
                        lemma="orange",
                        gloss="orange",
                        form="orange",
                        lemma_idx=20408,
                        pos_tag="ADJ",
                        morphology="Number=Sing|Definite=Def",
                        gram_raw="adj.sg.best",
                    ),
                    _cor_local_entry(
                        cor_id="COR.20408.303.01",
                        lemma="orange",
                        gloss="orange",
                        form="orange",
                        lemma_idx=20408,
                        pos_tag="ADJ",
                        morphology="Number=Plur",
                        gram_raw="adj.pl",
                    ),
                ],
            },
            by_form={
                "orange": [
                    _cor_local_entry(
                        cor_id="COR.20408.300.01",
                        lemma="orange",
                        gloss="orange",
                        form="orange",
                        lemma_idx=20408,
                        pos_tag="ADJ",
                        morphology="Gender=Com|Number=Sing|Definite=Ind",
                        gram_raw="adj.sg.ubest.fk",
                    ),
                    _cor_local_entry(
                        cor_id="COR.20408.301.01",
                        lemma="orange",
                        gloss="orange",
                        form="orange",
                        lemma_idx=20408,
                        pos_tag="ADJ",
                        morphology="Gender=Neut|Number=Sing|Definite=Ind",
                        gram_raw="adj.sg.ubest.itk",
                    ),
                    _cor_local_entry(
                        cor_id="COR.20408.302.01",
                        lemma="orange",
                        gloss="orange",
                        form="orange",
                        lemma_idx=20408,
                        pos_tag="ADJ",
                        morphology="Number=Sing|Definite=Def",
                        gram_raw="adj.sg.best",
                    ),
                    _cor_local_entry(
                        cor_id="COR.20408.303.01",
                        lemma="orange",
                        gloss="orange",
                        form="orange",
                        lemma_idx=20408,
                        pos_tag="ADJ",
                        morphology="Number=Plur",
                        gram_raw="adj.pl",
                    ),
                ],
            },
        ),
    )

    use_case.add_word(
        "orange",
        "orange",
        search_seed={
            "lemma": "orange",
            "surface": "orange",
            "cor_id": "COR.20408.300.01",
            "cor_lemma_idx": 20408,
            "meaning_key": "orange",
            "gloss": "orange",
            "english_translation": "orange",
            "pos_tag": "ADJ",
            "morphology": "Gender=Com|Number=Sing|Definite=Ind",
        },
    )

    details = use_case.get_lemma_details("orange")

    assert details.is_sectioned is True
    assert details.meaning_sections[0].gram_raw == (
        "adj.sg.ubest.fk | adj.sg.ubest.itk | adj.sg.best | adj.pl"
    )
    assert details.surface_forms[0].gram_raw == (
        "adj.sg.ubest.fk | adj.sg.ubest.itk | adj.sg.best | adj.pl"
    )


def test_wordbank_search_seed_repeat_save_repairs_surface_derived_meaning_metadata(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    initial_use_case = WordbankUseCase(db_path)
    initial_use_case.add_word(
        "lærere",
        "lærer",
        search_seed={
            "lemma": "lærer",
            "surface": "lærere",
            "cor_id": "COR.49032.112.01",
            "cor_lemma_idx": 49032,
            "meaning_key": "teacher",
            "gloss": "teacher",
            "english_translation": "teacher",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Plur|Definite=Ind",
        },
    )

    repaired_use_case = WordbankUseCase(
        db_path,
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_lemma_idx={
                49032: [
                    _cor_local_entry(
                        cor_id="COR.49032.110.01",
                        lemma="lærer",
                        gloss="teacher",
                        form="lærer",
                        lemma_idx=49032,
                        pos_tag="NOUN",
                        morphology="Gender=Com|Number=Sing|Definite=Ind",
                        gram_raw="sb.fk.sg.ubest",
                    ),
                    _cor_local_entry(
                        cor_id="COR.49032.112.01",
                        lemma="lærer",
                        gloss="teacher",
                        form="lærere",
                        lemma_idx=49032,
                        pos_tag="NOUN",
                        morphology="Gender=Com|Number=Plur|Definite=Ind",
                        gram_raw="sb.fk.pl.ubest",
                    ),
                ],
            },
        ),
    )

    repaired_use_case.add_word(
        "lærere",
        "lærer",
        search_seed={
            "lemma": "lærer",
            "surface": "lærere",
            "cor_id": "COR.49032.112.01",
            "cor_lemma_idx": 49032,
            "meaning_key": "teacher",
            "gloss": "teacher",
            "english_translation": "teacher",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Plur|Definite=Ind",
        },
    )

    details = repaired_use_case.get_lemma_details("lærer")

    assert details.morphology == "Gender=Com|Number=Sing|Definite=Ind"
    assert details.meaning_sections[0].morphology == "Gender=Com|Number=Sing|Definite=Ind"
    assert details.meaning_sections[0].surface_forms[0].morphology == "Gender=Com|Number=Plur|Definite=Ind"


def test_round_trip_word_page_search_seed_meanings_include_gloss_translation(tmp_path: Path) -> None:
    use_case = WordbankUseCase(
        _db_path(tmp_path),
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_lemma_idx={
                123: [
                    _cor_local_entry(
                        cor_id="COR.BOG.READING.LEM",
                        lemma="bog",
                        gloss="til læsning",
                        form="bog",
                        lemma_idx=123,
                        pos_tag="NOUN",
                        morphology="Gender=Com|Number=Sing|Definite=Ind",
                        gram_raw="sb.fk.sg.ubest",
                    ),
                ],
                124: [
                    _cor_local_entry(
                        cor_id="COR.BOG.BEECHMAST.LEM",
                        lemma="bog",
                        gloss="frugt fra et bøgetræ",
                        form="bog",
                        lemma_idx=124,
                        pos_tag="NOUN",
                        morphology="Gender=Neut|Number=Sing|Definite=Ind",
                        gram_raw="sb.itk.sg.ubest",
                    ),
                ],
            },
        ),
        translation_service=FakeTranslationService({
            "til læsning": "for reading",
            "frugt fra et bøgetræ": "fruit from a beech tree",
        }),
    )

    use_case.add_word(
        "bog",
        "bog",
        search_seed={
            "lemma": "bog",
            "surface": "bog",
            "cor_id": "COR.BOG.READING.LEM",
            "cor_lemma_idx": 123,
            "meaning_key": "for-reading",
            "gloss": "til læsning",
            "english_translation": "book",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Sing|Definite=Ind",
        },
    )
    use_case.add_word(
        "bog",
        "bog",
        search_seed={
            "lemma": "bog",
            "surface": "bog",
            "cor_id": "COR.BOG.BEECHMAST.LEM",
            "cor_lemma_idx": 124,
            "meaning_key": "beechmast",
            "gloss": "frugt fra et bøgetræ",
            "english_translation": "beechmast",
            "pos_tag": "NOUN",
            "morphology": "Gender=Neut|Number=Sing|Definite=Ind",
        },
    )

    details = use_case.get_lemma_details("bog")

    assert details.is_sectioned is True
    assert [section.english_translation for section in details.meaning_sections] == ["book", "beechmast"]
    assert [section.gloss_translation for section in details.meaning_sections] == [
        "for reading",
        "fruit from a beech tree",
    ]


def test_add_word_generates_non_cor_meaning_when_cor_is_missing(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    gemini_service = FakeGeminiWordTranslationService(
        {},
        non_cor_generation_overrides={
            ("superstort", "superstort", None): {
                "lemma": "superstor",
                "english_translation": "super big",
                "meaning_key": "very large",
                "gloss": "very large",
                "pos_tag": "ADJ",
                "morphology": "Degree=Pos|Number=Sing|Definite=Ind",
                "surface_pos_tag": "ADJ",
                "surface_morphology": "Degree=Pos|Gender=Neut|Number=Sing|Definite=Ind",
            },
        },
    )
    use_case = WordbankUseCase(
        db_path,
        gemini_word_translation_service=gemini_service,
    )

    result = use_case.add_word("superstort", "superstort")

    assert result.stored_lemma == "superstor"
    assert result.meaning is not None
    assert result.saved_snapshot is not None
    assert result.saved_snapshot.dictionary_status == "generated_non_cor"
    assert result.saved_snapshot.meaning_sections[0].dictionary_status == "generated_non_cor"
    assert [item.form for item in result.saved_snapshot.meaning_sections[0].surface_forms] == ["superstort"]


def test_complete_variations_uses_gemini_for_generated_non_cor_meanings(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    gemini_service = FakeGeminiWordTranslationService(
        {},
        non_cor_generation_overrides={
            ("superstort", "superstort", None): {
                "lemma": "superstor",
                "english_translation": "super big",
                "meaning_key": "very large",
                "gloss": "very large",
                "pos_tag": "ADJ",
                "morphology": "Degree=Pos|Number=Sing|Definite=Ind",
                "surface_pos_tag": "ADJ",
                "surface_morphology": "Degree=Pos|Gender=Neut|Number=Sing|Definite=Ind",
            },
        },
        non_cor_variation_overrides={
            ("superstor", "ADJ", "very large"): [
                {
                    "form": "superstor",
                    "pos_tag": "ADJ",
                    "morphology": "Degree=Pos|Gender=Com|Number=Sing|Definite=Ind",
                },
                {
                    "form": "superstort",
                    "pos_tag": "ADJ",
                    "morphology": "Degree=Pos|Gender=Neut|Number=Sing|Definite=Ind",
                },
                {
                    "form": "superstore",
                    "pos_tag": "ADJ",
                    "morphology": "Degree=Pos|Number=Plur|Definite=Def",
                },
            ],
        },
    )
    use_case = WordbankUseCase(
        db_path,
        gemini_word_translation_service=gemini_service,
        verification_service=FakeVerificationService(),
    )

    added = use_case.add_word("superstort", "superstort")
    assert added.meaning is not None
    use_case.verify_added_word("superstor", None, meaning_id=added.meaning.id)
    use_case.verify_added_word("superstor", "superstort", meaning_id=added.meaning.id)

    completed = use_case.complete_meaning_variations("superstor", meaning_id=added.meaning.id)

    assert completed.status == "updated"
    assert completed.added_surface_forms == ["superstor", "superstore"]
    assert completed.queued_verification_targets == []
    details = use_case.get_lemma_details("superstor")
    assert {item.form for item in details.meaning_sections[0].surface_forms} == {
        "superstor",
        "superstort",
        "superstore",
    }


def test_complete_variations_trusts_gemini_variation_resolution(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    gemini_service = FakeGeminiWordTranslationService(
        {},
        non_cor_generation_overrides={
            ("ukomfortabel", "ukomfortabel", None): {
                "lemma": "ukomfortabel",
                "english_translation": "uncomfortable",
                "meaning_key": "uncomfortable",
                "gloss": "uncomfortable",
                "pos_tag": "ADJ",
                "morphology": "Degree=Pos|Gender=Com|Number=Sing|Definite=Ind",
                "surface_pos_tag": "ADJ",
                "surface_morphology": "Degree=Pos|Gender=Com|Number=Sing|Definite=Ind",
            },
        },
        non_cor_variation_overrides={
            ("ukomfortabel", "ADJ", "uncomfortable"): [
                {
                    "form": "ukomfortabelt",
                    "pos_tag": "ADJ",
                    "morphology": "Degree=Pos|Gender=Neut|Number=Sing|Definite=Ind",
                },
                {
                    "form": "ukomfortable",
                    "pos_tag": "ADJ",
                    "morphology": "Degree=Pos|Number=Plur|Definite=Def",
                },
                {
                    "form": "mere ukomfortabel",
                    "pos_tag": "ADJ",
                    "morphology": "Degree=Cmp",
                },
                {
                    "form": "mest ukomfortabel",
                    "pos_tag": "ADJ",
                    "morphology": "Degree=Sup",
                },
            ],
        },
    )
    use_case = WordbankUseCase(
        db_path,
        gemini_word_translation_service=gemini_service,
        verification_service=FakeVerificationService(),
    )

    added = use_case.add_word(
        "ukomfortabel",
        "ukomfortabel",
        search_seed={
            "lemma": "ukomfortabel",
            "surface": "ukomfortabel",
            "dictionary_status": "generated_non_cor",
            "meaning_key": "uncomfortable",
            "gloss": "uncomfortable",
            "english_translation": "uncomfortable",
            "pos_tag": "ADJ",
            "morphology": "Degree=Pos|Gender=Com|Number=Sing|Definite=Ind",
        },
    )
    assert added.meaning is not None
    use_case.verify_added_word("ukomfortabel", None, meaning_id=added.meaning.id)

    completed = use_case.complete_meaning_variations("ukomfortabel", meaning_id=added.meaning.id)

    assert completed.status == "updated"
    assert completed.added_surface_forms == [
        "ukomfortabelt",
        "ukomfortable",
        "mere ukomfortabel",
        "mest ukomfortabel",
    ]
    details = use_case.get_lemma_details("ukomfortabel")
    assert {item.form for item in details.meaning_sections[0].surface_forms} == {
        "ukomfortabel",
        "ukomfortabelt",
        "ukomfortable",
        "mere ukomfortabel",
        "mest ukomfortabel",
    }


def test_generated_non_cor_related_words_render_without_cor_variants(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    gemini_service = FakeGeminiWordTranslationService(
        {},
        non_cor_generation_overrides={
            ("superstort", "superstort", None): {
                "lemma": "superstor",
                "english_translation": "super big",
                "meaning_key": "very large",
                "gloss": "very large",
                "pos_tag": "ADJ",
                "morphology": "Degree=Pos|Number=Sing|Definite=Ind",
                "surface_pos_tag": "ADJ",
                "surface_morphology": "Degree=Pos|Gender=Neut|Number=Sing|Definite=Ind",
            },
        },
    )
    use_case = WordbankUseCase(
        db_path,
        gemini_word_translation_service=gemini_service,
        gemini_related_words_service=FakeGeminiRelatedWordsService(
            {
                "superstor": [
                    ("super", "super", "ADV"),
                    ("stor", "large", "ADJ"),
                ],
            },
        ),
    )

    use_case.add_word("superstort", "superstort")
    use_case.process_queued_related_words("superstor")
    details = use_case.get_lemma_details("superstor")

    assert details.related_words.status == "ready"
    assert [item.lemma for item in details.related_words.items] == ["super", "stor"]
    assert all(item.display_variant is None for item in details.related_words.items)
