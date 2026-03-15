from __future__ import annotations

from pathlib import Path

from app.api.schemas.v1.wordbank import LemmaDetailsResponse
from app.db.migrations import get_connection
from app.services.cor_local import CORLocalEntry
from app.services.use_cases.wordbank import WordbankUseCase
from tests.helpers.factories import _cor_local_entry, _db_path
from tests.helpers.fakes import (
    FakeCORLocalLexiconService,
    FakeGeminiWordTranslationService,
    FakeTranslationService,
)

def test_add_word_persists_gemini_gloss_aware_translations(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    local_cor = FakeCORLocalLexiconService(
        by_form={
            "bog": [
                CORLocalEntry(
                    cor_id="COR.123.110.01",
                    lemma="bog",
                    gloss="book",
                    gram_raw="sb.fk.sg.ubest",
                    form="bog",
                    norm="N",
                    lemma_idx=123,
                    gram_code=110,
                    variation=1,
                    pos_tag="NOUN",
                    morphology="Gender=Com|Number=Sing|Definite=Ind",
                    features={"Gender": "Com", "Number": "Sing", "Definite": "Ind"},
                    extra_tags=[],
                ),
            ],
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
            ],
        }
    )
    use_case = WordbankUseCase(
        db_path,
        cor_local_lexicon_service=local_cor,
        translation_service=FakeTranslationService({"bog": "book-fallback", "bogen": "book-fallback"}),
        gemini_word_translation_service=FakeGeminiWordTranslationService(
            {
                ("bog", "bog", "book"): "book",
                ("bogen", "bog", "book"): "the book",
            }
        ),
    )

    use_case.add_word("Bogen", "bog")

    details = use_case.get_lemma_details("bog")

    with get_connection(db_path) as conn:
        meaning_row = conn.execute(
            """
            SELECT english_translation
            FROM lexeme_meanings
            WHERE lexeme_id = (SELECT id FROM lexemes WHERE lemma = ?)
            """,
            ("bog",),
        ).fetchone()
        surface_row = conn.execute(
            """
            SELECT form
            FROM surface_forms
            WHERE meaning_id = (SELECT id FROM lexeme_meanings WHERE lexeme_id = (SELECT id FROM lexemes WHERE lemma = ?))
              AND form = ?
            """,
            ("bog", "bogen"),
        ).fetchone()

    assert meaning_row is not None
    assert meaning_row["english_translation"] == "book"
    assert details.english_translation == "book"
    assert surface_row is not None
    assert surface_row["form"] == "bogen"

def test_contract_wordbank_sectioned_details_keep_lemma_translation_and_expose_translated_gloss(
    tmp_path: Path,
) -> None:
    db_path = _db_path(tmp_path)
    reading_lemma = _cor_local_entry(
        cor_id="COR.BOG.READING.LEM",
        lemma="bog",
        gloss="til læsning",
        form="bog",
        lemma_idx=123,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Ind",
        gram_raw="sb.fk.sg.ubest",
    )
    reading_surface = _cor_local_entry(
        cor_id="COR.BOG.READING.DEF",
        lemma="bog",
        gloss="til læsning",
        form="bogen",
        lemma_idx=123,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Def",
        gram_raw="sb.fk.sg.best",
    )
    use_case = WordbankUseCase(
        db_path,
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_form={
                "bog": [reading_lemma],
                "bogen": [reading_surface],
            },
            by_lemma_idx={123: [reading_lemma, reading_surface]},
        ),
        translation_service=FakeTranslationService({
            "en bog": "book",
            "til læsning": "for reading",
        }),
    )

    use_case.add_word("Bogen", "bog")

    details = use_case.get_lemma_details("bog")

    with get_connection(db_path) as conn:
        meaning_row = conn.execute(
            """
            SELECT gloss, english_translation
            FROM lexeme_meanings
            WHERE lexeme_id = (SELECT id FROM lexemes WHERE lemma = ?)
            """,
            ("bog",),
        ).fetchone()

    assert meaning_row is not None
    assert meaning_row["gloss"] == "til læsning"
    assert meaning_row["english_translation"] == "book"
    assert details.meaning_sections[0].gloss == "til læsning"
    assert details.meaning_sections[0].english_translation == "book"
    assert details.meaning_sections[0].gloss_translation == "for reading"
    assert [item.form for item in details.meaning_sections[0].surface_forms] == ["bogen"]
    surface = next(item for item in details.meaning_sections[0].surface_forms if item.form == "bogen")
    assert surface == LemmaDetailsResponse.SurfaceFormDetails(
        form="bogen",
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Def",
        lemma="bog",
        lemma_translation="book",
        gloss="til læsning",
        gloss_translation="for reading",
        gram_raw="sb.fk.sg.best",
        has_pronunciation=False,
    )

def test_contract_wordbank_sectioned_details_do_not_overwrite_lemma_translation_with_english_gloss(
    tmp_path: Path,
) -> None:
    db_path = _db_path(tmp_path)
    mother_lemma = _cor_local_entry(
        cor_id="COR.MOR.LEM",
        lemma="mor",
        gloss="person",
        form="mor",
        lemma_idx=51046,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Ind",
        gram_raw="sb.fk.sg.ubest",
    )
    use_case = WordbankUseCase(
        db_path,
        cor_local_lexicon_service=FakeCORLocalLexiconService(
            by_form={"mor": [mother_lemma]},
            by_lemma_idx={51046: [mother_lemma]},
        ),
        translation_service=FakeTranslationService({"en mor": "a mother", "person": "person"}),
    )

    use_case.add_word("Mor", "mor")
    details = use_case.get_lemma_details("mor")

    with get_connection(db_path) as conn:
        meaning_row = conn.execute(
            """
            SELECT gloss, english_translation
            FROM lexeme_meanings
            WHERE lexeme_id = (SELECT id FROM lexemes WHERE lemma = ?)
            """,
            ("mor",),
        ).fetchone()

    assert meaning_row is not None
    assert meaning_row["gloss"] == "person"
    assert meaning_row["english_translation"] == "mother"
    assert details.english_translation == "mother"
    assert details.meaning_sections[0].english_translation == "mother"
    assert details.meaning_sections[0].gloss_translation == "person"
    assert details.meaning_sections[0].surface_forms == []

def test_add_word_batches_gemini_only_for_lemma_translation(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    local_cor = FakeCORLocalLexiconService(
        by_form={
            "bog": [
                CORLocalEntry(
                    cor_id="COR.123.110.01",
                    lemma="bog",
                    gloss="book",
                    gram_raw="sb.fk.sg.ubest",
                    form="bog",
                    norm="N",
                    lemma_idx=123,
                    gram_code=110,
                    variation=1,
                    pos_tag="NOUN",
                    morphology="Gender=Com|Number=Sing|Definite=Ind",
                    features={"Gender": "Com", "Number": "Sing", "Definite": "Ind"},
                    extra_tags=[],
                ),
            ],
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
            ],
        }
    )
    gemini_translation = FakeGeminiWordTranslationService(
        {
            ("bog", "bog", "book"): "book",
            ("bogen", "bog", "book"): "the book",
        }
    )
    use_case = WordbankUseCase(
        db_path,
        cor_local_lexicon_service=local_cor,
        translation_service=FakeTranslationService({"bog": "book-fallback", "bogen": "book-fallback"}),
        gemini_word_translation_service=gemini_translation,
    )

    use_case.add_word("Bogen", "bog")

    assert gemini_translation.batch_calls == [[("bog", "bog", "book")]]
    assert gemini_translation.calls == []
